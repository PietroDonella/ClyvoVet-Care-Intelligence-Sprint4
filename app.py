from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from ia_clyvovet.avaliacao import texto_relatorio  # noqa: E402
from ia_clyvovet.cliente_api import ClienteApiError, carregar_api, mesclar_com_api  # noqa: E402
from ia_clyvovet.orquestrador import CareIntelligence  # noqa: E402
from ia_clyvovet.servico_http import Aplicacao, iniciar_servidor  # noqa: E402
from ia_clyvovet.validacao import DadosInvalidos  # noqa: E402


def _barra(score: int) -> str:
    cheio = round(score / 10)
    return "#" * cheio + "-" * (10 - cheio)


def imprimir_insight(insight) -> None:
    pet = insight.pet
    print("=" * 78)
    print(f"  {pet.nome}  |  {pet.especie}  |  {pet.idade}a  |  {pet.peso} kg  |  RFID {pet.rfid_uid}")
    print(f"  Tutor: {pet.tutor_nome}  ({pet.tutor_telefone})")
    internacao = pet.status_internacao or "Ambulatorial"
    gaiola = f"  gaiola {pet.gaiola}" if pet.gaiola else ""
    print(f"  Situação: {internacao}{gaiola}")
    print(f"  Conforto esperado: {insight.faixa_conforto}")
    print(f"  Risco: {insight.nivel_risco.upper()}  {_barra(insight.score_risco)}  {insight.score_risco}/100")
    print(f"  Ação priorizada: {insight.acao_priorizada}")
    print("-" * 78)
    if insight.alertas:
        print("  Alertas")
        for alerta in insight.alertas:
            print(f"    [{alerta.nivel.upper():8}] {alerta.titulo}")
            print(f"               {alerta.detalhe}")
    else:
        print("  Alertas: nenhum")
    print("-" * 78)
    print("  Recomendações de serviço")
    if insight.recomendacoes:
        for rec in insight.recomendacoes:
            print(f"    P{rec.prioridade}  ({rec.publico})  {rec.servico}")
            print(f"         {rec.motivo}")
    else:
        print("    Nenhuma no momento")
    print("-" * 78)
    print("  Mensagem ao tutor")
    print(f"    {insight.mensagem_tutor}")
    print("-" * 78)
    print("  Resumo clínico")
    print(f"    {insight.resumo_clinico}")
    print()


def _clinica_da_api(url: str) -> dict:
    local = json.loads((ROOT / "data" / "base_clinica.json").read_text(encoding="utf-8"))
    try:
        return mesclar_com_api(local, carregar_api(url))
    except (ClienteApiError, DadosInvalidos) as exc:
        raise SystemExit(f"Falha ao ler a API .NET em {url}: {exc}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CLYVO VET Care Intelligence — IA integrada da 4ª sprint."
    )
    parser.add_argument("--pet", type=int, default=None, help="Analisa apenas o id_pet informado.")
    parser.add_argument("--json", action="store_true", help="Imprime a fila em JSON.")
    parser.add_argument("--servidor", action="store_true", help="Sobe a interface e a API local.")
    parser.add_argument("--porta", type=int, default=8080, help="Porta do servidor. Padrão: 8080.")
    parser.add_argument("--api", default=None, help="URL da API .NET, se ela estiver no ar.")
    parser.add_argument("--relatorio", action="store_true", help="Imprime a avaliação da personalização e a fila.")
    parser.add_argument("--validar", action="store_true", help="Confere a base e encerra.")
    args = parser.parse_args()

    clinica = _clinica_da_api(args.api) if args.api else None
    try:
        ia = CareIntelligence(ROOT / "data", clinica=clinica)
    except DadosInvalidos as exc:
        raise SystemExit("Base clínica inválida:\n- " + "\n- ".join(exc.erros)) from exc

    if args.validar:
        print(f"Base válida: {len(ia.pets)} pets, {len(ia.leituras)} leituras.")
        return

    if args.relatorio:
        print(texto_relatorio(ia), end="")
        return

    if args.servidor:
        os.environ["CLYVO_HTTP_LOG"] = "1"
        aplicacao = Aplicacao(ROOT / "data", ROOT / "web", clinica=clinica)
        servidor = iniciar_servidor(aplicacao, "127.0.0.1", args.porta)
        host, porta = servidor.server_address[:2]
        print(f"CLYVO VET Care Intelligence em http://{host}:{porta}", flush=True)
        print("Plantão e visão do tutor na mesma origem. Ctrl+C encerra.", flush=True)
        try:
            servidor.serve_forever()
        except KeyboardInterrupt:
            print("\nServidor encerrado.")
        finally:
            servidor.server_close()
        return

    if args.pet is not None:
        if args.pet not in ia.pets_por_id:
            raise SystemExit(f"Pet {args.pet} não encontrado. IDs: {sorted(ia.pets_por_id)}")
        insights = [ia.analisar_pet(args.pet)]
    else:
        insights = ia.fila_prioridade()

    if args.json:
        print(json.dumps([item.to_dict() for item in insights], ensure_ascii=False, indent=2))
        return

    print("\nCLYVO VET  —  Care Intelligence")
    print("Fila de priorização (regras + recomendação + texto do prompt)\n")
    for insight in insights:
        imprimir_insight(insight)
    print("Legenda de risco: critico > alto > medio > baixo")
    print("A decisão terapêutica permanece com o veterinário responsável.\n")


if __name__ == "__main__":
    main()
