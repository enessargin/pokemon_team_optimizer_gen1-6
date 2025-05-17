import sys
from pathlib import Path
from typing import Optional, Set

import pandas as pd
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QCheckBox,
    QSpinBox,
    QComboBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHBoxLayout,
    QMessageBox,
    QWidget,
)

DEFAULT_CSV = Path("Pokemon.csv")   
MAX_DATASET_GEN = 6                
TEAM_SIZE_MAX = 6                   
TYPE_BONUS_DEFAULT = 20             

def load_data(
    csv_path: Path,
    *,
    max_gen: int,
    allow_mega: bool,
    allow_legendary: bool,
) -> pd.DataFrame:
    df = pd.read_csv(csv_path)

    df = df[df["Generation"] <= max_gen]

    if not allow_mega:
        df = df[~df["Name"].str.contains("Mega|Primal", regex=True)]

    if not allow_legendary:
        df = df[~df["Legendary"]]

    return df.reset_index(drop=True) 


def team_score(team: pd.DataFrame, *, type_bonus: int) -> int:
    base_power = team["Total"].sum()

    unique_types: Set[str] = set(team["Type 1"]) | set(team["Type 2"].dropna())

    return base_power + type_bonus * len(unique_types)


def greedy_team(df: pd.DataFrame, *, k: int, type_bonus: int) -> pd.DataFrame:
    chosen_idx = []          
    remaining = df.copy()    

    while len(chosen_idx) < k and not remaining.empty:
        best_idx: Optional[int] = None
        best_score = -float("inf")

        # Evaluate every candidate Pokémon in the remaining pool
        for idx, _ in remaining.iterrows():
            candidate_team = df.loc[chosen_idx + [idx]]
            score = team_score(candidate_team, type_bonus=type_bonus)
            if score > best_score:
                best_score = score
                best_idx = idx

        if best_idx is None:
            break

        chosen_idx.append(best_idx)     # lock the best pick
        remaining = remaining.drop(best_idx)

    return df.loc[chosen_idx]

class MainWindow(QWidget):

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pokémon Team Optimizer (Gen 1‑6)")
        self.resize(760, 520)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        # Row 1 – global filters (Mega / Legendary / Generation)
        top_row = QHBoxLayout()
        self.chk_mega = QCheckBox("Allow Mega / Primal", self)
        self.chk_legendary = QCheckBox("Allow Legendary / Mythical", self)
        top_row.addWidget(self.chk_mega)
        top_row.addWidget(self.chk_legendary)

        top_row.addWidget(QLabel("Max generation:"))
        self.combo_gen = QComboBox(self)
        for g in range(1, MAX_DATASET_GEN + 1):
            self.combo_gen.addItem(str(g), g)  
        self.combo_gen.setCurrentIndex(MAX_DATASET_GEN - 1)  # default = 6
        top_row.addWidget(self.combo_gen)

        top_row.addStretch()  
        root.addLayout(top_row)

        # Row 2 – hyper‑parameters (team size, type bonus)
        mid_row = QHBoxLayout()
        mid_row.addWidget(QLabel("Team size:"))
        self.spin_team = QSpinBox(self)
        self.spin_team.setRange(1, TEAM_SIZE_MAX)
        self.spin_team.setValue(TEAM_SIZE_MAX)
        mid_row.addWidget(self.spin_team)

        mid_row.addWidget(QLabel("Type bonus:"))
        self.spin_bonus = QSpinBox(self)
        self.spin_bonus.setRange(0, 100)
        self.spin_bonus.setValue(TYPE_BONUS_DEFAULT)
        mid_row.addWidget(self.spin_bonus)
        mid_row.addStretch()
        root.addLayout(mid_row)

        run_btn = QPushButton("Find best team", self)
        run_btn.clicked.connect(self._run_optimizer)
        root.addWidget(run_btn)

        # Results table
        self.table = QTableWidget(self)
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Name", "Type 1", "Type 2", "Total"])
        self.table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self.table, 1)  # stretch factor ⇒ table grows with window

        # Score label 
        self.lbl_score = QLabel("Score: –", self)
        big_font = self.lbl_score.font()
        big_font.setPointSize(12)
        self.lbl_score.setFont(big_font)
        self.lbl_score.setAlignment(Qt.AlignCenter)
        root.addWidget(self.lbl_score)

    def _run_optimizer(self) -> None:
        csv_path = DEFAULT_CSV
        if not csv_path.exists():
            QMessageBox.warning(self, "Dataset not found",
                                f"Cannot locate {csv_path!s} in the working directory.")
            return

        try:
            df = load_data(
                csv_path,
                max_gen=self.combo_gen.currentData(),
                allow_mega=self.chk_mega.isChecked(),
                allow_legendary=self.chk_legendary.isChecked(),
            )
        except Exception as exc:
            QMessageBox.critical(self, "Error reading CSV", str(exc))
            return

        if df.empty:
            QMessageBox.information(self, "No Pokémon",
                                     "Dataset is empty after applying filters.")
            return

        team = greedy_team(
            df,
            k=self.spin_team.value(),
            type_bonus=self.spin_bonus.value(),
        )
        score = team_score(team, type_bonus=self.spin_bonus.value())

        self._populate_table(team)
        self.lbl_score.setText(f"Score: {score}")

    def _populate_table(self, team: pd.DataFrame) -> None:
        self.table.setRowCount(len(team))
        for row_idx, (_, mon) in enumerate(team.iterrows()):
            self.table.setItem(row_idx, 0, QTableWidgetItem(mon["Name"]))
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(mon["Type 1"])))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(mon["Type 2"])))
            self.table.setItem(row_idx, 3, QTableWidgetItem(str(mon["Total"])))

        self.table.resizeColumnsToContents()

app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())


