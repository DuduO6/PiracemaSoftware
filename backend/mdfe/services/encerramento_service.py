import hashlib
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from mdfe.models import Manifesto, OperacaoEncerramento

from .certificate_service import load_configuration_material
from .consulta_service import ConsultaMdfeService
from .exceptions import MdfeCommunicationError, MdfeError
from .sefaz_client import SefazClient, child_text, find_mdfe_payload
from .validators import validate_municipality
from .xml_service import build_closing_event, serialize, validate_schema


SAO_PAULO = ZoneInfo("America/Sao_Paulo")


class EncerramentoMdfeService:
    def __init__(self, configuration):
        self.configuration = configuration
        self.consulta = ConsultaMdfeService(configuration)

    def close(self, manifesto, *, user, uf, municipality_code, closing_date, idempotency_key=""):
        municipality = validate_municipality(municipality_code, uf)
        if closing_date > datetime.now(SAO_PAULO).date():
            raise MdfeError("A data de encerramento não pode estar no futuro.", code="future_closing_date")
        if manifesto.cnpj_emitente[:8] != self.configuration.cnpj[:8]:
            raise MdfeError(
                "O MDF-e não pertence ao CNPJ-base da transportadora configurada.", code="manifest_company_mismatch"
            )
        if not idempotency_key:
            raw = f"{manifesto.pk}|{uf}|{municipality_code}|{closing_date.isoformat()}"
            idempotency_key = hashlib.sha256(raw.encode("utf-8")).hexdigest()
        idempotency_key = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()

        with transaction.atomic():
            locked = Manifesto.objects.select_for_update().get(pk=manifesto.pk)
            existing = OperacaoEncerramento.objects.filter(
                manifesto=locked, idempotency_key=idempotency_key
            ).first()
            if existing:
                return existing
            homologated = locked.operacoes_encerramento.filter(
                estado=OperacaoEncerramento.Estado.HOMOLOGADO
            ).first()
            if locked.situacao == Manifesto.Situacao.ENCERRADO and homologated:
                return homologated
            active = locked.operacoes_encerramento.filter(
                estado__in=(OperacaoEncerramento.Estado.PROCESSANDO, OperacaoEncerramento.Estado.A_CONFIRMAR)
            ).first()
            if active:
                if active.estado == OperacaoEncerramento.Estado.PROCESSANDO and active.solicitado_em < timezone.now() - timedelta(minutes=5):
                    active.estado = OperacaoEncerramento.Estado.A_CONFIRMAR
                    active.descricao_sefaz = "Operação interrompida; situação oficial deve ser confirmada."
                    active.save(update_fields=("estado", "descricao_sefaz"))
                    locked.situacao = Manifesto.Situacao.A_CONFIRMAR
                    locked.save(update_fields=("situacao", "atualizado_em"))
                raise MdfeError(
                    "Já existe um encerramento em processamento ou com situação a confirmar.",
                    code="closing_in_progress",
                    status_code=409,
                    details={"operation_id": str(active.id)},
                )
            operation = OperacaoEncerramento.objects.create(
                manifesto=locked,
                solicitado_por=user,
                idempotency_key=idempotency_key,
                identificador_evento=f"ID110112{locked.chave}01",
                uf=uf,
                municipio_codigo=str(municipality["id"]),
                municipio_nome=municipality["cidade"],
                data_encerramento=closing_date,
            )

        try:
            status = self.consulta.document_status(manifesto.chave)
            if status.code == "132":
                if not status.closing_protocol:
                    raise MdfeError(
                        "A SEFAZ informa o MDF-e encerrado, mas não retornou o protocolo do evento.",
                        code="closing_protocol_missing",
                        status_code=502,
                    )
                return self._homologate_from_status(operation, status)
            if status.code == "101":
                Manifesto.objects.filter(pk=manifesto.pk).update(
                    situacao=Manifesto.Situacao.CANCELADO,
                    ultimo_codigo_sefaz=status.code,
                    ultima_descricao_sefaz=status.description,
                )
                return self._finish_rejected(operation, status.code, status.description, status.raw_xml)
            if status.code != "100":
                return self._finish_rejected(operation, status.code, status.description, status.raw_xml)
            if status.authorization_protocol and status.authorization_protocol != manifesto.protocolo_autorizacao:
                return self._finish_rejected(
                    operation,
                    "222",
                    "Protocolo de autorização local difere do protocolo confirmado pela SEFAZ.",
                    status.raw_xml,
                )
            if status.authorization_datetime:
                authorized_at = parse_datetime(status.authorization_datetime)
                if authorized_at and closing_date < authorized_at.date():
                    return self._finish_rejected(
                        operation,
                        "615",
                        "Data de encerramento anterior à autorização do MDF-e.",
                        status.raw_xml,
                    )

            material = load_configuration_material(self.configuration)
            event, event_id = build_closing_event(
                self.configuration,
                manifesto,
                uf=uf,
                municipality_code=str(municipality["id"]),
                closing_date=closing_date,
                event_time=datetime.now(SAO_PAULO),
                material=material,
            )
            event_xml = serialize(event).decode("utf-8")
            OperacaoEncerramento.objects.filter(pk=operation.pk).update(
                xml_evento=event_xml, identificador_evento=event_id
            )
            response = SefazClient(self.configuration).send(
                "MDFeRecepcaoEvento", event, uf_code=manifesto.chave[:2]
            )
            payload = find_mdfe_payload(response.root, "retEventoMDFe")
            validate_schema(payload, "retEventoMDFe_v3.00.xsd")
            code = child_text(payload, "cStat")
            description = child_text(payload, "xMotivo")
            protocol = child_text(payload, "nProt")
            registered_at_value = child_text(payload, "dhRegEvento")
            response_xml = serialize(payload).decode("utf-8")
            if code == "135" and protocol:
                registered_at = parse_datetime(registered_at_value)
                return self._homologate(operation, code, description, protocol, registered_at, response_xml)
            if code == "631":
                confirmed = self.consulta.document_status(manifesto.chave)
                if confirmed.code == "132" and confirmed.closing_protocol:
                    return self._homologate_from_status(operation, confirmed)
            return self._finish_rejected(operation, code, description, response_xml)
        except MdfeCommunicationError as exc:
            if exc.inconclusive:
                return self._finish_pending(operation, exc.message)
            return self._finish_error(operation, exc.message)
        except MdfeError as exc:
            return self._finish_error(operation, exc.message)
        except Exception:
            return self._finish_error(operation, "Falha interna ao processar o encerramento do MDF-e.")

    def confirm_pending(self, operation):
        if operation.estado != OperacaoEncerramento.Estado.A_CONFIRMAR:
            return operation
        status = self.consulta.document_status(operation.manifesto.chave)
        if status.code == "132" and status.closing_protocol:
            return self._homologate_from_status(operation, status)
        operation.codigo_sefaz = status.code
        operation.descricao_sefaz = (
            "A SEFAZ ainda não confirmou o encerramento. " + (status.description or "")
        )[:255]
        operation.xml_retorno = status.raw_xml
        operation.save(update_fields=("codigo_sefaz", "descricao_sefaz", "xml_retorno"))
        return operation

    def _homologate_from_status(self, operation, status):
        registered_at = parse_datetime(status.closing_datetime) if status.closing_datetime else None
        return self._homologate(
            operation,
            "132",
            status.description or "Encerramento de MDF-e homologado",
            status.closing_protocol,
            registered_at,
            status.raw_xml,
        )

    def _homologate(self, operation, code, description, protocol, registered_at, response_xml):
        finished = timezone.now()
        with transaction.atomic():
            operation = OperacaoEncerramento.objects.select_for_update().get(pk=operation.pk)
            operation.estado = OperacaoEncerramento.Estado.HOMOLOGADO
            operation.codigo_sefaz = code
            operation.descricao_sefaz = description[:255]
            operation.protocolo = protocol
            operation.registrado_em = registered_at or finished
            operation.xml_retorno = response_xml
            operation.finalizado_em = finished
            operation.save()
            manifest = Manifesto.objects.select_for_update().get(pk=operation.manifesto_id)
            manifest.situacao = Manifesto.Situacao.ENCERRADO
            manifest.protocolo_encerramento = protocol
            manifest.encerrado_em = operation.registrado_em
            manifest.encerramento_uf = operation.uf
            manifest.encerramento_municipio_codigo = operation.municipio_codigo
            manifest.encerramento_municipio_nome = operation.municipio_nome
            manifest.ultimo_codigo_sefaz = code
            manifest.ultima_descricao_sefaz = description[:255]
            manifest.listado_ultima_consulta = False
            manifest.snapshot_fiscal = self._build_snapshot(manifest, operation, finished)
            manifest.xml_criptografado = None
            manifest.xml_status = Manifesto.XmlStatus.REMOVIDO
            manifest.xml_ultimo_erro = ""
            manifest.save()
        return operation

    @staticmethod
    def _build_snapshot(manifest, operation, created_at):
        return {
            "versao": 1,
            "gerado_em": created_at.isoformat(),
            "chave": manifest.chave,
            "numero": manifest.numero,
            "cnpj_emitente": manifest.cnpj_emitente,
            "data_emissao": manifest.data_emissao.isoformat() if manifest.data_emissao else None,
            "protocolo_autorizacao": manifest.protocolo_autorizacao,
            "protocolo_encerramento": operation.protocolo,
            "encerrado_em": operation.registrado_em.isoformat() if operation.registrado_em else None,
            "encerramento": {
                "uf": operation.uf,
                "municipio_codigo": operation.municipio_codigo,
                "municipio_nome": operation.municipio_nome,
            },
            "destinos": manifest.destinos,
            "condutores": [
                {
                    "nome": conductor.motorista.nome if conductor.motorista_id else conductor.nome_xml,
                    "cpf_final": conductor.cpf[-2:],
                    "motorista_id": conductor.motorista_id,
                }
                for conductor in manifest.condutores.select_related("motorista").all()
            ],
            "xml_sha256": manifest.xml_sha256,
            "xml_fonte": manifest.xml_fonte,
            "xml_assinatura_conteudo_validada": manifest.xml_assinatura_conteudo_validada,
            "xml_classificacao": manifest.xml_classificacao,
            "dados_xml_somente_informativos": (
                manifest.xml_classificacao == Manifesto.XmlClassificacao.INFORMATIVO
            ),
        }

    def _finish_rejected(self, operation, code, description, response_xml):
        operation.estado = OperacaoEncerramento.Estado.REJEITADO
        operation.codigo_sefaz = code or ""
        operation.descricao_sefaz = (description or "Evento rejeitado pela SEFAZ.")[:255]
        operation.xml_retorno = response_xml
        operation.finalizado_em = timezone.now()
        operation.save(update_fields=(
            "estado", "codigo_sefaz", "descricao_sefaz", "xml_retorno", "finalizado_em"
        ))
        return operation

    def _finish_pending(self, operation, description):
        finished = timezone.now()
        with transaction.atomic():
            operation.estado = OperacaoEncerramento.Estado.A_CONFIRMAR
            operation.descricao_sefaz = description[:255]
            operation.finalizado_em = finished
            operation.save(update_fields=("estado", "descricao_sefaz", "finalizado_em"))
            Manifesto.objects.filter(pk=operation.manifesto_id).update(
                situacao=Manifesto.Situacao.A_CONFIRMAR,
                ultimo_codigo_sefaz="",
                ultima_descricao_sefaz=description[:255],
            )
        return operation

    def _finish_error(self, operation, description):
        operation.estado = OperacaoEncerramento.Estado.ERRO
        operation.descricao_sefaz = description[:255]
        operation.finalizado_em = timezone.now()
        operation.save(update_fields=("estado", "descricao_sefaz", "finalizado_em"))
        return operation
