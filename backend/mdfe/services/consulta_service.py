from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from mdfe.models import ConsultaManifestos, Manifesto

from .exceptions import MdfeCommunicationError, MdfeError, MdfeRejectionError
from .portal_download_service import PortalNacionalMdfeClient
from .sefaz_client import SefazClient, child_text, find_mdfe_payload
from .validators import access_key_data, validate_access_key
from .xml_service import build_non_closed_query, build_status_query, secure_parse, serialize, validate_schema
from .xml_import_service import MdfeXmlImportService


@dataclass
class DocumentStatus:
    code: str
    description: str
    authorization_protocol: str = ""
    authorization_datetime: str = ""
    closing_protocol: str = ""
    closing_datetime: str = ""
    raw_xml: str = ""


def validate_status_payload(payload):
    """Valida o retorno da SVRS, incluindo eventos retornados diretamente no envelope.

    O XSD de consulta trata o conteúdo de ``procEventoMDFe`` como um único elemento
    genérico, embora a resposta processada contenha ``eventoMDFe`` e ``retEventoMDFe``.
    A SVRS também pode devolver ``retEventoMDFe`` diretamente. Cada retorno de evento
    é validado pelo seu XSD oficial e removido somente da cópia usada para validar o
    envelope. O XML original permanece intacto para extração e auditoria.
    """
    for event in payload.xpath(".//*[local-name()='retEventoMDFe']"):
        validate_schema(event, "retEventoMDFe_v3.00.xsd")

    validation_copy = secure_parse(serialize(payload))
    for event in validation_copy.xpath(".//*[local-name()='retEventoMDFe']"):
        event.getparent().remove(event)
    validate_schema(validation_copy, "retConsSitMDFe_v3.00.xsd")


class ConsultaMdfeService:
    def __init__(self, configuration):
        self.configuration = configuration

    def refresh_non_closed(self, user):
        audit = ConsultaManifestos.objects.create(empresa=self.configuration.empresa, solicitado_por=user)
        try:
            response = SefazClient(self.configuration).send(
                "MDFeConsNaoEnc", build_non_closed_query(self.configuration)
            )
            payload = find_mdfe_payload(response.root, "retConsMDFeNaoEnc")
            validate_schema(payload, "retConsMDFeNaoEnc_v3.00.xsd")
            code = child_text(payload, "cStat")
            description = child_text(payload, "xMotivo")
            if code not in ("111", "112"):
                raise MdfeRejectionError(description or "Consulta rejeitada pela SEFAZ.", sefaz_code=code)

            found = []
            for info in payload.xpath(".//*[local-name()='infMDFe']"):
                key = validate_access_key(child_text(info, "chMDFe"))
                protocol = child_text(info, "nProt")
                if not protocol.isdigit() or len(protocol) != 15:
                    raise MdfeError(
                        "A SEFAZ retornou protocolo de autorização inválido.",
                        code="invalid_sefaz_protocol",
                        status_code=502,
                    )
                found.append((key, protocol, access_key_data(key)))

            finished = timezone.now()
            response_xml = serialize(payload).decode("utf-8")
            with transaction.atomic():
                Manifesto.objects.filter(
                    empresa=self.configuration.empresa,
                    situacao=Manifesto.Situacao.ABERTO,
                ).update(
                    situacao=Manifesto.Situacao.DESCONHECIDO,
                    listado_ultima_consulta=False,
                    ultima_consulta_em=finished,
                    ultimo_codigo_sefaz=code,
                    ultima_descricao_sefaz="Não retornado na consulta atual de não encerrados.",
                )
                for key, protocol, key_data in found:
                    Manifesto.objects.update_or_create(
                        empresa=self.configuration.empresa,
                        chave=key,
                        defaults={
                            "numero": key_data["number"],
                            "cnpj_emitente": key_data["issuer_cnpj"],
                            "protocolo_autorizacao": protocol,
                            "situacao": Manifesto.Situacao.ABERTO,
                            "listado_ultima_consulta": True,
                            "ultima_consulta_em": finished,
                            "ultimo_codigo_sefaz": code,
                            "ultima_descricao_sefaz": description,
                        },
                    )
            xml_result = self._hydrate_xmls([key for key, _, _ in found])
            audit.estado = ConsultaManifestos.Estado.SUCESSO
            audit.codigo_sefaz = code
            audit.descricao_sefaz = description
            audit.quantidade = len(found)
            audit.xml_baixados = xml_result["downloaded"]
            audit.xml_em_cache = xml_result["cached"]
            audit.xml_erros = xml_result["errors"]
            audit.resposta_xml = response_xml
            audit.finalizada_em = timezone.now()
            audit.save(update_fields=(
                "estado", "codigo_sefaz", "descricao_sefaz", "quantidade", "xml_baixados",
                "xml_em_cache", "xml_erros", "resposta_xml", "finalizada_em"
            ))
            return audit
        except Exception as exc:
            error = exc if isinstance(exc, MdfeError) else MdfeError(
                "Falha inesperada ao consultar a SEFAZ.", code="unexpected_consultation_error", status_code=500
            )
            audit.estado = ConsultaManifestos.Estado.ERRO
            audit.categoria_erro = error.code
            audit.descricao_sefaz = error.message
            audit.finalizada_em = timezone.now()
            audit.save(update_fields=("estado", "categoria_erro", "descricao_sefaz", "finalizada_em"))
            raise error

    def _hydrate_xmls(self, access_keys):
        result = {"downloaded": 0, "cached": 0, "errors": 0}
        if not access_keys:
            return result
        manifests = {
            manifest.chave: manifest
            for manifest in Manifesto.objects.filter(
                empresa=self.configuration.empresa, chave__in=access_keys
            ).only("id", "chave", "xml_criptografado", "xml_status")
        }
        pending = []
        for key in access_keys:
            manifest = manifests[key]
            if manifest.xml_criptografado and manifest.xml_status == Manifesto.XmlStatus.DISPONIVEL:
                result["cached"] += 1
            else:
                pending.append(manifest)
        if not pending:
            return result

        importer = MdfeXmlImportService(self.configuration)
        try:
            with PortalNacionalMdfeClient(self.configuration) as portal:
                for index, manifest in enumerate(pending):
                    attempted_at = timezone.now()
                    try:
                        xml_bytes = portal.download_xml(manifest.chave)
                        importer.import_document(xml_bytes, source=Manifesto.XmlFonte.PORTAL_NACIONAL)
                        result["downloaded"] += 1
                    except MdfeError as exc:
                        self._record_xml_error(manifest.pk, attempted_at, exc.message)
                        result["errors"] += 1
                        if exc.code == "mdfe_portal_rate_limited":
                            for remaining in pending[index + 1:]:
                                self._record_xml_error(remaining.pk, attempted_at, exc.message)
                                result["errors"] += 1
                            break
                    except Exception:
                        self._record_xml_error(
                            manifest.pk, attempted_at, "Falha inesperada ao processar o XML do MDF-e."
                        )
                        result["errors"] += 1
        except MdfeError as exc:
            attempted_at = timezone.now()
            for manifest in pending:
                self._record_xml_error(manifest.pk, attempted_at, exc.message)
                result["errors"] += 1
        except Exception:
            attempted_at = timezone.now()
            for manifest in pending:
                self._record_xml_error(
                    manifest.pk, attempted_at, "Falha inesperada ao acessar o Portal Nacional do MDF-e."
                )
                result["errors"] += 1
        return result

    @staticmethod
    def _record_xml_error(manifest_id, attempted_at, message):
        Manifesto.objects.filter(pk=manifest_id, xml_criptografado__isnull=True).update(
            xml_status=Manifesto.XmlStatus.ERRO,
            xml_ultima_tentativa_em=attempted_at,
            xml_ultimo_erro=(message or "Falha ao obter o XML.")[:255],
        )

    def document_status(self, access_key):
        response = SefazClient(self.configuration).send(
            "MDFeConsulta",
            build_status_query(self.configuration, access_key),
            uf_code=access_key[:2],
        )
        payload = find_mdfe_payload(response.root, "retConsSitMDFe")
        validate_status_payload(payload)
        code = child_text(payload, "cStat")
        description = child_text(payload, "xMotivo")
        authorization_protocol = ""
        authorization_datetime = ""
        protocol_nodes = payload.xpath(".//*[local-name()='protMDFe']/*[local-name()='infProt']")
        if protocol_nodes:
            authorization_protocol = child_text(protocol_nodes[0], "nProt")
            authorization_datetime = child_text(protocol_nodes[0], "dhRecbto")

        closing_protocol = ""
        closing_datetime = ""
        for event in payload.xpath(".//*[local-name()='retEventoMDFe']/*[local-name()='infEvento']"):
            if child_text(event, "tpEvento") == "110112" and child_text(event, "cStat") in ("135", "134"):
                candidate = child_text(event, "nProt")
                if candidate:
                    closing_protocol = candidate
                    closing_datetime = child_text(event, "dhRegEvento")
        return DocumentStatus(
            code=code,
            description=description,
            authorization_protocol=authorization_protocol,
            authorization_datetime=authorization_datetime,
            closing_protocol=closing_protocol,
            closing_datetime=closing_datetime,
            raw_xml=serialize(payload).decode("utf-8"),
        )
