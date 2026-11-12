import hashlib
import re
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.db import IntegrityError, transaction
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from mdfe.models import Manifesto
from mdfe.services.certificate_service import decrypt_secret
from mdfe.services.exceptions import MdfeError
from mdfe.services.validators import access_key_data, validate_access_key
from mdfe.services.xml_import_service import parse_mdfe_proc_xml
from motoristas.models import Motorista

from viagens.models import ImportacaoMdfeViagem, Viagem
from viagens.serializers import ViagemSerializer
from viagens.services.viagem_service import MOTORISTA_NAO_ENCONTRADO, salvar_viagem_validada


CENTAVOS = Decimal("0.01")
DESCONTO_CTE = Decimal("0.10")


def _text(node, name):
    values = node.xpath(f"./*[local-name()='{name}']/text()")
    return str(values[0]).strip() if values else ""


def _decimal(value):
    try:
        return Decimal(str(value or "").replace(",", ".").strip())
    except (InvalidOperation, ValueError):
        return None


def _money(value):
    return value.quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def _digits(value):
    return re.sub(r"\D", "", str(value or ""))


def validar_chave_cte(value):
    key = str(value or "").strip()
    if not re.fullmatch(r"\d{44}", key) or key[20:22] != "57":
        raise MdfeError("O XML contém uma chave de CT-e inválida.", code="invalid_cte_key", status_code=409)
    total = sum(
        int(digit) * weight
        for digit, weight in zip(reversed(key[:-1]), [2, 3, 4, 5, 6, 7, 8, 9] * 6)
    )
    remainder = total % 11
    expected = 0 if remainder in (0, 1) else 11 - remainder
    if int(key[-1]) != expected:
        raise MdfeError(
            "O XML contém uma chave de CT-e com dígito verificador inválido.",
            code="invalid_cte_key",
            status_code=409,
        )
    return key


def dados_chave_cte(key):
    key = validar_chave_cte(key)
    return {
        "chave": key,
        "serie": str(int(key[22:25])),
        "numero": str(int(key[25:34])),
    }


def _municipios(nodes, uf):
    values = []
    seen = set()
    for node in nodes:
        code = _text(node, "cMunCarrega") or _text(node, "cMunDescarga")
        name = _text(node, "xMunCarrega") or _text(node, "xMunDescarga")
        if code and name and code not in seen:
            values.append({"codigo": code, "municipio": name, "uf": uf})
            seen.add(code)
    return values


def _peso(info):
    total_nodes = info.xpath("./*[local-name()='tot']")
    if len(total_nodes) != 1:
        return None, "", "Peso total não informado no MDF-e."
    quantity = _decimal(_text(total_nodes[0], "qCarga"))
    unit = _text(total_nodes[0], "cUnid")
    if quantity is None or quantity <= 0:
        return None, unit, "Peso total inválido ou ausente no MDF-e."
    if unit == "01":
        return quantity / Decimal("1000"), unit, ""
    if unit == "02":
        return quantity, unit, ""
    return None, unit, "Unidade de peso desconhecida; informe o peso manualmente."


def _contratos(info):
    result = []
    for payment in info.xpath(
        ".//*[local-name()='infModal']/*[local-name()='rodo']"
        "/*[local-name()='infANTT']/*[local-name()='infPag']"
    ):
        components = []
        for component in payment.xpath("./*[local-name()='Comp']"):
            amount = _decimal(_text(component, "vComp"))
            components.append({
                "tipo": _text(component, "tpComp"),
                "descricao": _text(component, "xComp"),
                "valor": f"{amount:.2f}" if amount is not None else "",
            })
        contract = _decimal(_text(payment, "vContrato"))
        document = _digits(_text(payment, "CPF") or _text(payment, "CNPJ"))
        result.append({
            "valor": f"{contract:.2f}" if contract is not None else "",
            "indicador_pagamento": _text(payment, "indPag"),
            "componentes": components,
            "parcelas": len(payment.xpath("./*[local-name()='infPrazo']")),
            "tomador_nome": _text(payment, "xNome"),
            "tomador_documento_mascarado": f"***{document[-2:]}" if document else "",
        })
    return result


def extrair_dados_viagem_mdfe(manifesto, usuario):
    if not manifesto.xml_criptografado or manifesto.xml_status != Manifesto.XmlStatus.DISPONIVEL:
        raise MdfeError(
            "O XML deste MDF-e não está disponível para preparar a viagem.",
            code="mdfe_xml_unavailable",
            status_code=409,
        )

    xml_bytes = decrypt_secret(manifesto.xml_criptografado)
    if manifesto.xml_sha256 and hashlib.sha256(xml_bytes).hexdigest() != manifesto.xml_sha256:
        raise MdfeError(
            "O conteúdo armazenado do MDF-e não corresponde ao resumo registrado.",
            code="mdfe_xml_hash_mismatch",
            status_code=409,
        )
    root = parse_mdfe_proc_xml(xml_bytes)
    info_nodes = root.xpath("./*[local-name()='MDFe']/*[local-name()='infMDFe']")
    protocol_nodes = root.xpath("./*[local-name()='protMDFe']/*[local-name()='infProt']")
    if len(info_nodes) != 1 or len(protocol_nodes) != 1:
        raise MdfeError("Estrutura do MDF-e processado inválida.", code="invalid_stored_mdfe_xml", status_code=409)

    info = info_nodes[0]
    protocol = protocol_nodes[0]
    key = validate_access_key(info.get("Id", "").removeprefix("MDFe"))
    if key != manifesto.chave or validate_access_key(_text(protocol, "chMDFe")) != key:
        raise MdfeError("O XML armazenado não corresponde ao manifesto.", code="stored_mdfe_key_mismatch", status_code=409)
    if _text(protocol, "cStat") != "100":
        raise MdfeError("O XML não contém protocolo de autorização cStat 100.", code="xml_not_authorized", status_code=409)
    protocol_number = _text(protocol, "nProt")
    if not protocol_number or protocol_number != manifesto.protocolo_autorizacao:
        raise MdfeError("O protocolo do XML difere do manifesto consultado.", code="xml_protocol_mismatch", status_code=409)

    issuer = info.xpath("string(./*[local-name()='emit']/*[local-name()='CNPJ'])").strip()
    key_data = access_key_data(key)
    if issuer != manifesto.cnpj_emitente or issuer != key_data["issuer_cnpj"]:
        raise MdfeError("O emitente do XML não corresponde ao manifesto.", code="xml_issuer_mismatch", status_code=409)
    xml_number = info.xpath("string(./*[local-name()='ide']/*[local-name()='nMDF'])").strip()
    xml_series = info.xpath("string(./*[local-name()='ide']/*[local-name()='serie'])").strip()
    if not xml_number.isdigit() or int(xml_number) != int(key_data["number"]):
        raise MdfeError("O número do XML não corresponde à chave do MDF-e.", code="xml_number_mismatch", status_code=409)
    if not xml_series.isdigit() or int(xml_series) != int(key[22:25]):
        raise MdfeError("A série do XML não corresponde à chave do MDF-e.", code="xml_series_mismatch", status_code=409)

    cte_keys = []
    for raw_key in info.xpath(
        "./*[local-name()='infDoc']/*[local-name()='infMunDescarga']"
        "/*[local-name()='infCTe']/*[local-name()='chCTe']/text()"
    ):
        key_value = validar_chave_cte(str(raw_key).strip())
        if key_value not in cte_keys:
            cte_keys.append(key_value)
    ctes = [dados_chave_cte(key_value) for key_value in cte_keys]

    origin_uf = info.xpath("string(./*[local-name()='ide']/*[local-name()='UFIni'])").strip()
    destination_uf = info.xpath("string(./*[local-name()='ide']/*[local-name()='UFFim'])").strip()
    origins = _municipios(
        info.xpath("./*[local-name()='ide']/*[local-name()='infMunCarrega']"),
        origin_uf,
    )
    destinations = _municipios(
        info.xpath("./*[local-name()='infDoc']/*[local-name()='infMunDescarga']"),
        destination_uf,
    )

    weight_ton, weight_unit, weight_warning = _peso(info)
    contracts = _contratos(info)
    payer_names = {
        contract["tomador_nome"].strip()
        for contract in contracts
        if contract["tomador_nome"].strip()
    }
    suggested_customer = next(iter(payer_names)) if len(payer_names) == 1 else ""
    contract_value = None
    if len(contracts) == 1:
        parsed_contract = _decimal(contracts[0]["valor"])
        if parsed_contract is not None and parsed_contract > 0:
            contract_value = parsed_contract

    suggested_rate = None
    if len(ctes) == 1 and weight_ton and weight_ton > 0 and contract_value:
        suggested_rate = _money(contract_value / weight_ton)

    registered_by_cpf = {
        _digits(driver.cpf): driver
        for driver in Motorista.objects.filter(usuario=usuario).order_by("id")
    }
    drivers = []
    seen_cpfs = set()
    for node in info.xpath(
        ".//*[local-name()='infModal']/*[local-name()='rodo']//*[local-name()='condutor']"
    ):
        cpf = _digits(_text(node, "CPF"))
        if not cpf or cpf in seen_cpfs:
            continue
        match = registered_by_cpf.get(cpf)
        drivers.append({
            "nome": _text(node, "xNome"),
            "cpf": cpf,
            "cpf_mascarado": f"***.***.***-{cpf[-2:]}",
            "motorista_id": match.id if match else None,
            "motorista_nome": match.nome if match else "",
        })
        seen_cpfs.add(cpf)

    selected_driver = drivers[0]["motorista_id"] if len(drivers) == 1 else None
    emitted_text = info.xpath("string(./*[local-name()='ide']/*[local-name()='dhEmi'])").strip()
    emitted_at = parse_datetime(emitted_text)
    if emitted_at is None:
        raise MdfeError("A data de emissão do XML é inválida.", code="invalid_stored_mdfe_xml", status_code=409)

    product_nodes = info.xpath("./*[local-name()='prodPred']")
    product = {
        "nome": _text(product_nodes[0], "xProd") if product_nodes else "",
        "tipo": _text(product_nodes[0], "tpCarga") if product_nodes else "",
    }
    vehicle_plate = info.xpath(
        "string(.//*[local-name()='infModal']/*[local-name()='rodo']"
        "/*[local-name()='veicTracao']/*[local-name()='placa'])"
    ).strip()

    return {
        "manifesto": manifesto,
        "chave_mdfe": key,
        "numero_mdfe": str(int(key_data["number"])),
        "serie_mdfe": str(int(key[22:25])),
        "data_emissao": emitted_at,
        "protocolo": protocol_number,
        "ctes": ctes,
        "condutores": drivers,
        "origens": origins,
        "destinos": destinations,
        "peso_toneladas": weight_ton,
        "unidade_peso": weight_unit,
        "aviso_peso": weight_warning,
        "contratos": contracts,
        "valor_contrato": contract_value,
        "valor_tonelada_sugerido": suggested_rate,
        "cliente_sugerido": suggested_customer,
        "produto": product,
        "placa": vehicle_plate,
        "motorista_sugerido_id": selected_driver,
        "xml_informativo": manifesto.xml_classificacao == Manifesto.XmlClassificacao.INFORMATIVO,
        "assinatura_validada": manifesto.xml_assinatura_conteudo_validada,
    }


def _publicar_preview(extracted, usuario, empresa):
    manifest = extracted["manifesto"]
    mdfe_import = ImportacaoMdfeViagem.objects.filter(empresa=empresa, chave_mdfe=manifest.chave).first()
    cte_duplicate = None
    if len(extracted["ctes"]) == 1:
        cte_duplicate = ImportacaoMdfeViagem.objects.filter(
            empresa=empresa,
            chave_cte=extracted["ctes"][0]["chave"],
        ).first()
    historical = []
    for cte in extracted["ctes"]:
        ids = list(
            Viagem.objects.filter(usuario=usuario, teve_cte=True, numero_cte=cte["numero"])
            .values_list("id", flat=True)[:5]
        )
        if ids:
            historical.append({"numero_cte": cte["numero"], "viagens": ids})

    pending = []
    if len(extracted["ctes"]) > 1:
        pending.append("Selecione qual CT-e corresponde à viagem.")
    if not extracted["ctes"]:
        pending.append("O manifesto não possui CT-e vinculado.")
    if len(extracted["origens"]) != 1:
        pending.append("Revise o município de origem.")
    if len(extracted["destinos"]) != 1:
        pending.append("Revise o município de destino.")
    if not extracted["peso_toneladas"]:
        pending.append(extracted["aviso_peso"] or "Informe o peso em toneladas.")
    if not extracted["motorista_sugerido_id"]:
        pending.append(MOTORISTA_NAO_ENCONTRADO)
    if not extracted["cliente_sugerido"]:
        pending.append("Informe o cliente/tomador antes de salvar.")
    if historical:
        pending.append("Há viagem histórica com o mesmo número de CT-e; confirme após revisar.")

    already_imported = bool(mdfe_import or cte_duplicate)
    if already_imported:
        status_code = "JA_IMPORTADO"
        status_label = "Já importado"
    elif len(extracted["ctes"]) > 1:
        status_code = "MULTIPLOS_CTE"
        status_label = "Múltiplos CT-e"
    elif pending or extracted["xml_informativo"]:
        status_code = "NECESSITA_CONFIRMACAO" if extracted["xml_informativo"] else "DADOS_INCOMPLETOS"
        status_label = "Necessita confirmação" if extracted["xml_informativo"] else "Dados incompletos"
    else:
        status_code = "PRONTO_REVISAO"
        status_label = "Pronto para revisão"

    weight = extracted["peso_toneladas"]
    contract = extracted["valor_contrato"]
    suggested = extracted["valor_tonelada_sugerido"]
    financial = None
    if weight and suggested:
        gross = _money(weight * suggested)
        discount = _money(gross * DESCONTO_CTE)
        net = _money(gross - discount)
        financial = {
            "valor_bruto": f"{gross:.2f}",
            "desconto_cte": f"{discount:.2f}",
            "valor_liquido": f"{net:.2f}",
            "diferenca_contrato": f"{_money(net - contract):.2f}" if contract else "",
        }

    return {
        "chave_mdfe": extracted["chave_mdfe"],
        "numero_mdfe": extracted["numero_mdfe"],
        "serie_mdfe": extracted["serie_mdfe"],
        "data_emissao": extracted["data_emissao"].isoformat(),
        "protocolo": extracted["protocolo"],
        "situacao": manifest.situacao,
        "ctes": extracted["ctes"],
        "condutores": [
            {key: value for key, value in driver.items() if key != "cpf"}
            for driver in extracted["condutores"]
        ],
        "origens": extracted["origens"],
        "destinos": extracted["destinos"],
        "peso_toneladas": f"{weight:.2f}" if weight else "",
        "unidade_peso": extracted["unidade_peso"],
        "aviso_peso": extracted["aviso_peso"],
        "contratos": extracted["contratos"],
        "valor_contrato": f"{contract:.2f}" if contract else "",
        "valor_tonelada_sugerido": f"{suggested:.2f}" if suggested else "",
        "cliente_sugerido": extracted["cliente_sugerido"],
        "produto": extracted["produto"],
        "placa": extracted["placa"],
        "motorista_sugerido_id": extracted["motorista_sugerido_id"],
        "xml_informativo": extracted["xml_informativo"],
        "assinatura_validada": extracted["assinatura_validada"],
        "status": status_code,
        "status_label": status_label,
        "pendencias": pending,
        "possiveis_duplicidades": historical,
        "viagem_id": mdfe_import.viagem_id if mdfe_import else (cte_duplicate.viagem_id if cte_duplicate else None),
        "financeiro_sugerido": financial,
        "sugestao": {
            "motorista_id": extracted["motorista_sugerido_id"],
            "data": extracted["data_emissao"].date().isoformat(),
            "origem": extracted["origens"][0]["municipio"] if len(extracted["origens"]) == 1 else "",
            "destino": extracted["destinos"][0]["municipio"] if len(extracted["destinos"]) == 1 else "",
            "cliente": extracted["cliente_sugerido"],
            "peso": f"{weight:.2f}" if weight else "",
            "valor_tonelada": f"{suggested:.2f}" if suggested else "",
            "teve_cte": bool(extracted["ctes"]),
            "descontar_cte": bool(extracted["ctes"]),
            "chave_cte": extracted["ctes"][0]["chave"] if len(extracted["ctes"]) == 1 else "",
            "pago": False,
        },
    }


def preparar_manifestos(manifestos, usuario, empresa):
    items = []
    for manifest in manifestos:
        if not manifest.xml_criptografado or manifest.xml_status != Manifesto.XmlStatus.DISPONIVEL:
            items.append({
                "chave_mdfe": manifest.chave,
                "numero_mdfe": str(int(manifest.numero)) if manifest.numero.isdigit() else manifest.numero,
                "status": "XML_INDISPONIVEL",
                "status_label": "XML indisponível",
                "pendencias": [manifest.xml_ultimo_erro or "O XML completo ainda não está disponível."],
                "sugestao": {},
            })
            continue
        try:
            items.append(_publicar_preview(extrair_dados_viagem_mdfe(manifest, usuario), usuario, empresa))
        except MdfeError as exc:
            items.append({
                "chave_mdfe": manifest.chave,
                "numero_mdfe": str(int(manifest.numero)) if manifest.numero.isdigit() else manifest.numero,
                "status": "DADOS_INCOMPLETOS",
                "status_label": "Dados incompletos",
                "pendencias": [exc.message],
                "sugestao": {},
            })
    return items


def importar_viagens_confirmadas(*, empresa, usuario, request, registros):
    mdfe_keys = [item["mdfe_chave"] for item in registros]
    if len(mdfe_keys) != len(set(mdfe_keys)):
        raise MdfeError("O mesmo MDF-e foi enviado mais de uma vez.", code="duplicate_mdfe_in_request", status_code=409)

    try:
        with transaction.atomic():
            manifests = {
                item.chave: item
                for item in Manifesto.objects.select_for_update().filter(
                    empresa=empresa,
                    chave__in=mdfe_keys,
                    situacao=Manifesto.Situacao.ABERTO,
                )
            }
            if len(manifests) != len(mdfe_keys):
                raise MdfeError(
                    "Um ou mais MDF-e não estão abertos ou não pertencem à empresa selecionada.",
                    code="mdfe_not_available_for_import",
                    status_code=409,
                )

            existing = set(
                ImportacaoMdfeViagem.objects.select_for_update()
                .filter(empresa=empresa, chave_mdfe__in=mdfe_keys)
                .values_list("chave_mdfe", flat=True)
            )
            if existing:
                raise MdfeError(
                    "Um ou mais MDF-e selecionados já foram importados.",
                    code="mdfe_already_imported",
                    status_code=409,
                    details={"chaves": sorted(existing)},
                )

            created = []
            selected_ctes = set()
            for index, item in enumerate(registros):
                extracted = extrair_dados_viagem_mdfe(manifests[item["mdfe_chave"]], usuario)
                driver = Motorista.objects.filter(id=item["motorista_id"], usuario=usuario).first()
                if not driver:
                    raise MdfeError(
                        MOTORISTA_NAO_ENCONTRADO,
                        code="driver_not_registered",
                        status_code=400,
                        details={"indice": index},
                    )

                xml_driver_cpfs = {driver_item["cpf"] for driver_item in extracted["condutores"]}
                selected_cpf = _digits(driver.cpf)
                if xml_driver_cpfs and selected_cpf not in xml_driver_cpfs and not item["confirmar_divergencia_cpf"]:
                    raise MdfeError(
                        "O CPF do motorista selecionado difere do MDF-e. Confirme a divergência para continuar.",
                        code="driver_cpf_mismatch_confirmation_required",
                        status_code=409,
                        details={"indice": index},
                    )
                if extracted["xml_informativo"] and not item["confirmar_xml_informativo"]:
                    raise MdfeError(
                        "Revise e confirme os dados extraídos antes de salvar.",
                        code="informational_xml_confirmation_required",
                        status_code=409,
                        details={"indice": index},
                    )

                available_ctes = {cte["chave"]: cte for cte in extracted["ctes"]}
                selected_cte_key = item.get("chave_cte", "")
                if len(available_ctes) == 1 and not selected_cte_key:
                    selected_cte_key = next(iter(available_ctes))
                if available_ctes:
                    if not item["teve_cte"] or selected_cte_key not in available_ctes:
                        raise MdfeError(
                            "Selecione um CT-e pertencente ao MDF-e para continuar.",
                            code="cte_selection_required",
                            status_code=400,
                            details={"indice": index},
                        )
                    cte = available_ctes[selected_cte_key]
                    if selected_cte_key in selected_ctes:
                        raise MdfeError("O mesmo CT-e foi selecionado mais de uma vez.", code="duplicate_cte_in_request", status_code=409)
                    selected_ctes.add(selected_cte_key)
                    if ImportacaoMdfeViagem.objects.select_for_update().filter(
                        empresa=empresa,
                        chave_cte=selected_cte_key,
                    ).exists():
                        raise MdfeError("O CT-e selecionado já foi importado.", code="cte_already_imported", status_code=409)
                    historical_exists = Viagem.objects.filter(
                        usuario=usuario,
                        teve_cte=True,
                        numero_cte=cte["numero"],
                    ).exists()
                    if historical_exists and not item["confirmar_possivel_duplicidade"]:
                        raise MdfeError(
                            "Já existe uma viagem com o mesmo número de CT-e. Confirme após revisar.",
                            code="historical_cte_confirmation_required",
                            status_code=409,
                            details={"indice": index},
                        )
                else:
                    if item["teve_cte"] or selected_cte_key:
                        raise MdfeError(
                            "O MDF-e não possui CT-e vinculado; não informe um CT-e.",
                            code="cte_not_in_mdfe",
                            status_code=400,
                            details={"indice": index},
                        )
                    cte = None

                if extracted["valor_contrato"] and item["teve_cte"]:
                    gross = _money(item["peso"] * item["valor_tonelada"])
                    discount = _money(gross * DESCONTO_CTE) if item["descontar_cte"] else Decimal("0.00")
                    net = _money(gross - discount)
                    if net != _money(extracted["valor_contrato"]) and not item["confirmar_diferenca_contrato"]:
                        raise MdfeError(
                            "O valor líquido calculado difere do contrato do MDF-e. Confirme a diferença para continuar.",
                            code="contract_difference_confirmation_required",
                            status_code=409,
                            details={"indice": index},
                        )

                trip_data = {
                    "motorista": driver.id,
                    "data": item["data"],
                    "origem": item["origem"],
                    "destino": item["destino"],
                    "cliente": item["cliente"],
                    "peso": item["peso"],
                    "valor_tonelada": item["valor_tonelada"],
                    "teve_cte": bool(cte),
                    "descontar_cte": bool(cte) and item["descontar_cte"],
                    "numero_cte": cte["numero"] if cte else "",
                    "pago": item["pago"],
                }
                serializer = ViagemSerializer(data=trip_data, context={"request": request})
                if not serializer.is_valid():
                    raise MdfeError(
                        "Confira os dados da viagem selecionada.",
                        code="invalid_trip_data",
                        status_code=400,
                        details={"indice": index, "erros": serializer.errors},
                    )
                trip = salvar_viagem_validada(serializer, usuario)
                ImportacaoMdfeViagem.objects.create(
                    viagem=trip,
                    empresa=empresa,
                    manifesto=extracted["manifesto"],
                    chave_mdfe=extracted["chave_mdfe"],
                    chave_cte=cte["chave"] if cte else None,
                    xml_sha256=extracted["manifesto"].xml_sha256,
                    criado_por=usuario,
                )
                created.append(trip)
            return created
    except IntegrityError as exc:
        raise MdfeError(
            "Outro processo já importou um MDF-e ou CT-e selecionado.",
            code="concurrent_mdfe_import",
            status_code=409,
        ) from exc
    except serializers.ValidationError as exc:
        raise MdfeError(
            "Confira o motorista selecionado.",
            code="invalid_driver",
            status_code=400,
            details={"erros": exc.detail},
        ) from exc
