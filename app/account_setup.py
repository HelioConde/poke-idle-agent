"""Assistente local para CADASTRAR conta/roster de qualquer espécie sem código fixo.

Não acessa navegador, credenciais ou servidores. Nunca publique arquivos
gerados em data/ (já ignorado pelo Git). Contas = apelidos, não login.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Callable

from app.adaptive_strategy import Account

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_DATA = ROOT / "data"


def _alias(prompt: str, ask: Callable[[str], str]) -> str:
    answer = ask(prompt).strip()
    if not answer or "@" in answer or len(answer) > 64 or any(ord(c) < 32 for c in answer):
        raise ValueError("Informe apenas um apelido local sem e-mail ou credenciais")
    return answer


def _level(prompt: str, ask: Callable[[str], str]) -> int | None:
    answer = ask(prompt).strip()
    if not answer:
        return None
    if not answer.isdecimal() or not 1 <= int(answer) <= 100000:
        raise ValueError("Nível inválido")
    return int(answer)


def collect_account(ask: Callable[[str], str] = input) -> Account:
    print("Cadastro local: use apelidos, nunca e-mail, senha ou tokens.")
    game = ask("Jogo [world/io]: ").strip().lower()
    profile = _alias("Apelido do perfil: ", ask)
    alias = _alias("Apelido da conta: ", ask)
    trainer = _level("Nível do treinador [Enter se desconhecido]: ", ask)
    roster = []
    while True:
        species = ask("Espécie do Pokémon [Enter para terminar equipe]: ").strip()
        if not species:
            break
        item_id = _alias("Identificador local do Pokémon: ", ask)
        level = _level("Nível do Pokémon: ", ask)
        if level is None:
            raise ValueError("O Pokémon precisa ter um nível informado")
        roster.append({"id": item_id, "species": species, "level": level})
        if len(roster) > 100:
            raise ValueError("Máximo de 100 Pokémon")
    active = None
    if roster:
        active = ask("ID do Pokémon ativo [Enter se desconhecido]: ").strip() or None
    hunts = []
    while True:
        label = ask("Nome da hunt [Enter para terminar]: ").strip()
        if not label:
            break
        hunt_id = _alias("Identificador local da hunt: ", ask)
        state = ask("Já desbloqueada? [s/n/?]: ").strip().lower()
        if state not in ("s", "n", "?"):
            raise ValueError("Responda s, n ou ?")
        required = _level("Nível exigido do treinador [Enter se não souber]: ", ask)
        hunts.append({"id":hunt_id, "label":label,
                      "unlocked":True if state=="s" else False if state=="n" else None,
                      "required_trainer_level":required})
        if len(hunts) > 200:
            raise ValueError("Máximo de 200 hunts")
    return Account.parse({
        "game":game, "profile_id":profile, "account_id":alias,
        "trainer_level":trainer, "roster":roster,
        "active_pokemon_id":active, "hunts":hunts
    })


def save_account(account: Account, path: Path = PRIVATE_DATA / "accounts.json") -> None:
    target = path.resolve()
    if not target.is_relative_to(PRIVATE_DATA.resolve()) or target.suffix.lower() != ".json":
        raise ValueError("Cadastre somente em data/*.json, fora do Git")
    target.parent.mkdir(parents=True, exist_ok=True)
    previous = []
    if target.exists():
        previous = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(previous,list):
            raise ValueError("Formato existente inválido")
    # Validar também registros antigos; não sobrescrever contas duplicadas.
    existing=[Account.parse(raw) for raw in previous]
    if account.key in {item.key for item in existing}:
        raise ValueError("Conta já cadastrada; recuse sobrescrita automática")
    from dataclasses import asdict
    updated=previous + [asdict(account)]
    temporary=target.with_suffix(".tmp")
    with temporary.open("x",encoding="utf-8") as stream:
        json.dump(updated,stream,ensure_ascii=False,indent=2)
        stream.write("\n")
    os.replace(temporary,target)


def main() -> None:
    parser=argparse.ArgumentParser(description="Cadastrar contas localmente sem login")
    parser.add_argument("--out",type=Path,default=PRIVATE_DATA / "accounts.json")
    args=parser.parse_args()
    account=collect_account()
    save_account(account,args.out)
    print("Conta adicionada ao JSON privado: ",args.out)
    print("Próximo passo: python -m app.adaptive_strategy --accounts data/accounts.json")


if __name__=="__main__":
    main()
