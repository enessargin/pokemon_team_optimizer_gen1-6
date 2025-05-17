
from itertools import combinations
import argparse
import pandas as pd
from pathlib import Path

MAX_GENERATION  = 6        # use only Gen 1-6
ALLOW_MEGA      = False    # keep Mega / Primal forms?
ALLOW_LEGENDARY = False    # keep Legendaries / Mythicals?
TYPE_BONUS      = 20       # how much a *new* type is worth
TEAM_SIZE       = 6

def load_data(csv_path: Path,
              max_gen=MAX_GENERATION,
              allow_mega=ALLOW_MEGA,
              allow_legendary=ALLOW_LEGENDARY) -> pd.DataFrame:
    
    df = pd.read_csv(csv_path)
    df = df[df["Generation"] <= max_gen]

    if not allow_mega:
        df = df[~df["Name"].str.contains("Mega|Primal", regex=True)]

    if not allow_legendary:
        df = df[~df["Legendary"]]

    df = df.reset_index(drop=True)
    return df


def team_score(team: pd.DataFrame, type_bonus: int = TYPE_BONUS) -> int:
    stat_sum = team["Total"].sum()

    types = set(team["Type 1"]) | set(team["Type 2"].dropna())
    return stat_sum + type_bonus * len(types)


def greedy_team(df: pd.DataFrame,
                k: int = TEAM_SIZE,
                type_bonus: int = TYPE_BONUS) -> pd.DataFrame:
 
    chosen_idx = []
    remaining  = df.copy()

    while len(chosen_idx) < k:
        best_idx   = None
        best_delta = -float("inf")

        for idx, row in remaining.iterrows():
            new_team   = df.loc[chosen_idx + [idx]]
            delta      = team_score(new_team, type_bonus)
            if delta > best_delta:
                best_delta = delta
                best_idx   = idx

        chosen_idx.append(best_idx)
        remaining = remaining.drop(best_idx)

    return df.loc[chosen_idx]



parser = argparse.ArgumentParser(description="Find a strong, diverse Pokémon team.")
parser.add_argument("--csv", default="Pokemon.csv", help="Path to Pokémon dataset CSV")
parser.add_argument("--allow-mega",      action="store_true", help="Include Mega / Primal forms")
parser.add_argument("--allow-legendary", action="store_true", help="Include Legendaries / Mythicals")
parser.add_argument("--type-bonus", type=int, default=TYPE_BONUS, help="Bonus per unique type")
parser.add_argument("--team-size",  type=int, default=TEAM_SIZE, help="Number of Pokémon to pick")
args = parser.parse_args()

df   = load_data(args.csv, allow_mega=args.allow_mega, allow_legendary=args.allow_legendary)
team = greedy_team(df, k=args.team_size, type_bonus=args.type_bonus)
score = team_score(team, args.type_bonus)

print(f"\n=== Best team (score {score}) ===")
print(team[["Name", "Type 1", "Type 2", "Total"]].to_string(index=False))


