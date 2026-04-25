from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
import requests

class DataExtraction:
    _HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def __init__(self, char):
        self.data = f'http://ufcstats.com/statistics/fighters?char={char.lower()}&page=all'
        self.char = char.lower()

    def get_data(self):
        page = requests.get(self.data, headers=self._HEADERS)
        self.soup = BeautifulSoup(page.text, 'html.parser')
        self.row_data = self.soup.find_all("tr")

    def get_headers(self):
        self.table_headers = []
        headers = self.soup.find_all("th")
        for header in headers:
            self.table_headers.append(header.text.strip())
    
    def set_dataframe(self):
        self.dataframe = pd.DataFrame(columns = self.table_headers)
        return(self.dataframe)

    def get_urls(self):
        self.urls = []
        self.stats = []
        for row in self.row_data:
            cell_data = row.find_all("td")
            length = len(self.dataframe)
            row_info = [data.text.strip() for data in cell_data]
            try:
                self.dataframe.loc[length] = row_info
            except ValueError:
                pass
            for tag in cell_data:
                reference_url = tag.find('a')
                if reference_url:
                    self.urls.append(reference_url['href'])
        self.urls = [
            link for i, link in enumerate(self.urls)
            if link not in self.urls[:i]]
        self.urls = [sublist for sublist in self.urls if sublist]

    def set_dataframe_urls(self):
            self.dataframe['UFC Link'] = self.urls
            return(self.dataframe)

    def to_csv(self, path=None):
        if path is None:
            path = f'training_data/fighters_{self.char}.csv'
        self.fight_history_df.to_csv(path, index=False)
        return path

    def scrape_page(self, csv_path=None):
        self.get_data()
        self.get_headers()
        self.set_dataframe()
        self.get_urls()
        self.set_dataframe_urls()
        self.collect_all_fight_histories()
        return self.to_csv(csv_path)

    def find_fighter(self, fighter):
        fighter_split_name = fighter.split(" ")
        fighter_firstname = fighter_split_name[0]
        fighter_lastname = " ".join(fighter_split_name[1:])
        
        mask = (
            (self.dataframe['First'] == fighter_firstname) & 
            (self.dataframe['Last'] == fighter_lastname)
        )

        index = self.dataframe.index[mask]
        self.link = list(self.dataframe.loc[index, 'UFC Link'])
        return(self.dataframe.iloc[index])
    
    def get_fighter_info(self):
        url = self.link[0]
        page = requests.get(url, headers=self._HEADERS)
        soup = BeautifulSoup(page.text, 'html.parser')
        row_data = soup.find_all("tr")

        self.individual_row_data = []
        for row in row_data:
            cell_data = row.find_all("td")
            row_info = []
            for cell in cell_data:
                row_info.append(cell.get_text(strip=True, separator=" "))
            self.individual_row_data.append(row_info)

        self.individual_row_data = [
            row for row in self.individual_row_data
            if any(cell.strip() for cell in row)
        ]
        self.table_headers_fighter = []
        title_headers = soup.find_all("th")
        for header in title_headers:
            self.table_headers_fighter.append(header.text.strip())

    def set_fighthistory_dataframe(self):
        self.dataframe_fighthistory = pd.DataFrame(columns = self.table_headers_fighter)
        for row in self.individual_row_data:
            if len(row) == len(self.table_headers_fighter):    
                length = len(self.dataframe_fighthistory)
                self.dataframe_fighthistory.loc[length] = row
        #else:
        #  print(len(row), len(self.table_headers_fighter))

    def clean_data(self):
        self.dataframe_fighthistory[["Td_fighter", "Td_opponent"]] = (
            self.dataframe_fighthistory["Td"].astype(str).str.split(" ", expand=True)
        )

        self.dataframe_fighthistory[["Kd_fighter", "Kd_opponent"]] = (
            self.dataframe_fighthistory["Kd"].astype(str).str.split(" ", expand=True)
        )

        split_names = (
            self.dataframe_fighthistory["Fighter"].astype(str).str.split(" ", expand=True)
        )

        self.dataframe_fighthistory["Fighter"] = (
            split_names.loc[:, 0:1].apply(lambda row: " ".join(row.dropna()), axis=1)
        )
        self.dataframe_fighthistory["Opponent"] = (
            split_names.loc[:, 2:].apply(lambda row: " ".join(row.dropna()), axis=1)
        )

        self.dataframe_fighthistory[["Str_fighter", "Str_opponent"]] = (
            self.dataframe_fighthistory["Str"].astype(str).str.split(" ", expand=True)
        )

        self.dataframe_fighthistory[["Sub_fighter", "Sub_opponent"]] = (
            self.dataframe_fighthistory["Sub"].astype(str).str.split(" ", expand=True)
        )

        reorder = [
            "W/L", "Fighter", "Opponent", "Kd_fighter", "Kd_opponent",
            "Str_fighter", "Str_opponent", "Td_fighter", "Td_opponent",
            "Sub_fighter", "Sub_opponent", "Event", "Method", "Round", "Time"
        ]
        self.dataframe_fighthistory['Round'] = self.dataframe_fighthistory['Round'].astype(int)
        self.dataframe_fighthistory = self.dataframe_fighthistory[reorder]  

    def get_opponents_stance(self):
        stances = []
        opponents = self.dataframe_fighthistory['Opponent'].tolist()
        stance_df = pd.DataFrame({"Opponents":opponents})
        last_name_initials = [opponent.split(" ", 1)[1][0] for opponent in opponents]
        for i in range(len(opponents)):
            fighter = DataExtraction(last_name_initials[i])
            fighter.get_data()
            fighter.get_headers()
            fighter.set_dataframe()
            fighter.get_urls()
            fighter.set_dataframe_urls()
            temp_df = fighter.find_fighter(opponents[i])
            stance = temp_df['Stance'].iloc[0]
            stances.append(stance)
        stance_df["Stance"] = stances
        return(stance_df)
    
    def get_career_stats(self, url=None):
        if url is None:
            url = self.link[0]
        page = requests.get(url, headers=self._HEADERS)
        soup = BeautifulSoup(page.text, 'html.parser')
        li_data = soup.find_all("li", class_='b-list__box-list-item b-list__box-list-item_type_block')
        career_stats = []
        for row in li_data:
            career_stats.append(row.get_text(strip=True))
        career_stats = career_stats[5::]
        career_stats.pop(4)
        keys = []
        values = []
        for stat in career_stats:
            keys.append(stat.split(':')[0])
            values.append(stat.split(':')[1])
        for i in range(len(values)):
            if '%' in values[i]:
                values[i] = int(values[i][:-1])/100
        return dict(zip(keys, values))

    def _get_ctrl_times(self, fight_url):
        try:
            page = requests.get(fight_url, headers=self._HEADERS, timeout=10)
            soup = BeautifulSoup(page.text, 'html.parser')
            for table in soup.find_all("table"):
                ths = [th.get_text(strip=True) for th in table.find_all("th")]
                if "Ctrl" not in ths:
                    continue
                ctrl_idx = ths.index("Ctrl")
                data_rows = [r for r in table.find_all("tr") if r.find("td")]
                if not data_rows:
                    continue
                tds = data_rows[0].find_all("td")
                if ctrl_idx >= len(tds):
                    continue
                ps = [p.get_text(strip=True) for p in tds[ctrl_idx].find_all("p")]
                return (ps[0] if ps else "0:00", ps[1] if len(ps) > 1 else "0:00")
        except Exception:
            pass
        return "0:00", "0:00"

    def get_fight_history(self, url, fighter_name):
        page = requests.get(url, headers=self._HEADERS)
        soup = BeautifulSoup(page.text, 'html.parser')

        headers = [th.text.strip() for th in soup.find_all("th")]
        if not headers:
            return pd.DataFrame()
        headers.append("Date")
        headers.append("f_ctrl")
        headers.append("o_ctrl")

        event_idx = headers.index("Event") if "Event" in headers else None

        raw_rows = []
        fight_urls = []
        for tr in soup.find_all(
            "tr",
            class_="b-fight-details__table-row b-fight-details__table-row__hover js-fight-details-click"
        ):
            cells = tr.find_all("td")
            if not cells:
                continue
            row = [cell.get_text(strip=True, separator=" ") for cell in cells]
            date = "NA"
            if event_idx is not None and event_idx < len(cells):
                p_tags = cells[event_idx].find_all("p", class_="b-fight-details__table-text")
                if len(p_tags) >= 2:
                    date = p_tags[1].get_text(strip=True)
            row.append(date)
            raw_rows.append(row)
            fight_urls.append(tr.get("data-link", ""))

        if not raw_rows:
            return pd.DataFrame()

        def fetch_ctrl(u):
            return self._get_ctrl_times(u) if u else ("0:00", "0:00")

        with ThreadPoolExecutor(max_workers=10) as ex:
            ctrl_results = list(ex.map(fetch_ctrl, fight_urls))

        rows = []
        for row, (f_ctrl, o_ctrl) in zip(raw_rows, ctrl_results):
            row.append(f_ctrl)
            row.append(o_ctrl)
            if len(row) == len(headers) and any(v.strip() for v in row):
                rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=headers)
        df.insert(0, "Fighter_Name", fighter_name)
        return df

    def collect_all_fight_histories(self):
        def fetch_one(i):
            try:
                row = self.dataframe.iloc[i]
                fighter_name = f"{row['First']} {row['Last']}".strip()
                return self.get_fight_history(self.urls[i], fighter_name)
            except Exception:
                return pd.DataFrame()

        with ThreadPoolExecutor(max_workers=5) as ex:
            results = list(ex.map(fetch_one, range(len(self.urls))))

        all_dfs = [df for df in results if not df.empty]
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            dedup_cols = [c for c in ["Fighter", "Event", "Date"] if c in combined.columns]
            self.fight_history_df = combined.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
            self.clean_fight_history()
            self.compute_prefight_stats()
        else:
            self.fight_history_df = pd.DataFrame()

    def _map_method(self, method_str):
        m = str(method_str).strip().upper()
        if "DECISION" in m or m in ("U-DEC", "S-DEC", "M-DEC"):
            return "DEC"
        if "KO" in m or "TKO" in m:
            return "KO/TKO"
        if "SUBMISSION" in m or "SUB" in m:
            return "SUB"
        return "other"

    def clean_fight_history(self):
        df = self.fight_history_df

        df[["Td_fighter", "Td_opponent"]] = df["Td"].astype(str).str.split(" ", expand=True)
        df[["Kd_fighter", "Kd_opponent"]] = df["Kd"].astype(str).str.split(" ", expand=True)
        df[["Str_fighter", "Str_opponent"]] = df["Str"].astype(str).str.split(" ", expand=True)
        df[["Sub_fighter", "Sub_opponent"]] = df["Sub"].astype(str).str.split(" ", expand=True)

        split_names = df["Fighter"].astype(str).str.split(" ", expand=True)
        df["Fighter"] = split_names.loc[:, 0:1].apply(lambda row: " ".join(row.dropna()), axis=1)
        df["Opponent"] = split_names.loc[:, 2:].apply(lambda row: " ".join(row.dropna()), axis=1)

        df["winner"] = df.apply(
            lambda row: row["Fighter"] if row["W/L"].strip().lower() in ("w", "win")
            else (row["Opponent"] if row["W/L"].strip().lower() in ("l", "loss") else "Draw"),
            axis=1
        )

        df["method"] = df["Method"].apply(self._map_method)

        def _ctrl_to_seconds(val):
            try:
                parts = str(val).strip().split(":")
                return int(parts[0]) * 60 + int(parts[1])
            except Exception:
                return 0.0

        df["f_ctrl"] = df["f_ctrl"].apply(_ctrl_to_seconds)
        df["o_ctrl"] = df["o_ctrl"].apply(_ctrl_to_seconds)

        for col in ["Str_fighter", "Str_opponent", "Td_fighter", "Td_opponent", "Round"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["Date"] = pd.to_datetime(df["Date"], format="mixed", errors="coerce")
        self.fight_history_df = df

    def compute_prefight_stats(self):
        df = self.fight_history_df.copy()

        def parse_minutes(row):
            try:
                parts = str(row["Time"]).strip().split(":")
                return (row["Round"] - 1) * 5 + int(parts[0]) + int(parts[1]) / 60
            except Exception:
                return row["Round"] * 5

        df["fight_minutes"] = df.apply(parse_minutes, axis=1)

        # Build full history from both perspectives so each fighter's record is complete
        forward = df[["Fighter", "W/L", "Str_fighter", "Str_opponent",
                       "Td_fighter", "Method", "fight_minutes", "f_ctrl", "Date"]].copy()
        forward.columns = ["name", "wl", "str_landed", "str_absorbed", "td", "method", "minutes", "ctrl", "date"]

        backward = df[["Opponent", "W/L", "Str_opponent", "Str_fighter",
                        "Td_opponent", "Method", "fight_minutes", "o_ctrl", "Date"]].copy()
        backward.columns = ["name", "wl", "str_landed", "str_absorbed", "td", "method", "minutes", "ctrl", "date"]
        backward["wl"] = backward["wl"].apply(
            lambda x: "L" if str(x).strip().lower() in ("w", "win")
            else ("W" if str(x).strip().lower() in ("l", "loss") else "D")
        )

        full_history = pd.concat([forward, backward], ignore_index=True).sort_values("date")

        def stats_for(name, before_date):
            prior = full_history[(full_history["name"] == name) & (full_history["date"] < before_date)]
            n = len(prior)
            if n == 0:
                return {k: 0.0 for k in ["SLpM", "SApM", "TD_pct", "W_pct", "KO_pct", "Sub_pct", "Finish_pct", "ctrl"]}
            total_min = prior["minutes"].sum() or 1
            wins = prior[prior["wl"].str.strip().str.lower().isin(["w", "win"])]
            n_wins = len(wins)
            last5 = prior.tail(5)
            n_last5_wins = last5["wl"].str.strip().str.lower().isin(["w", "win"]).sum()
            ko_wins = wins["method"].str.contains("KO|TKO", case=False, na=False).sum()
            sub_wins = wins["method"].str.contains("Sub", case=False, na=False).sum()
            finishes = (~prior["method"].str.contains("Decision", case=False, na=False)).sum()
            return {
                "SLpM":        round(prior["str_landed"].sum() / total_min, 3),
                "SApM":        round(prior["str_absorbed"].sum() / total_min, 3),
                "TD_pct":      round(prior["td"].sum() / n, 3),
                "W_pct":       round(n_last5_wins / len(last5), 3),
                "KO_pct":      round(ko_wins / max(n_wins, 1), 3),
                "Sub_pct":     round(sub_wins / max(n_wins, 1), 3),
                "Finish_pct":  round(finishes / n, 3),
                "ctrl":        round(prior["ctrl"].mean(), 3),
            }

        fighter_stats = df.apply(lambda row: stats_for(row["Fighter"], row["Date"]), axis=1)
        opponent_stats = df.apply(lambda row: stats_for(row["Opponent"], row["Date"]), axis=1)

        f_df = pd.DataFrame(fighter_stats.tolist()).add_prefix("f_")
        o_df = pd.DataFrame(opponent_stats.tolist()).add_prefix("o_")

        keep = ["W/L", "winner", "method", "Round", "Date", "Fighter", "Opponent"]
        self.fight_history_df = pd.concat(
            [df[keep].reset_index(drop=True), f_df, o_df], axis=1
        )
        self._compute_elo(df)
        self._compute_survivor_score(df)

    def _compute_elo(self, df):
        import math

        df_sorted = df.sort_values("Date").reset_index(drop=True)
        elo = {}
        f_elos = [0.0] * len(df_sorted)
        o_elos = [0.0] * len(df_sorted)

        for i, row in df_sorted.iterrows():
            fighter = row["Fighter"]
            opponent = row["Opponent"]
            winner = row["winner"]

            f_elo = elo.get(fighter, 1000.0)
            o_elo = elo.get(opponent, 1000.0)
            f_elos[i] = f_elo
            o_elos[i] = o_elo

            diff = abs(f_elo - o_elo)
            if diff == 0:
                change = f_elo * 0.008
            elif diff <= 30:
                change = diff
            elif diff <= 100:
                change = math.ceil(diff * 0.7)
            else:
                change = diff * 0.07

            if winner == fighter:
                elo[fighter] = f_elo + change
                elo[opponent] = o_elo - change
            elif winner == opponent:
                elo[fighter] = f_elo - change
                elo[opponent] = o_elo + change

        df_sorted["f_ELO"] = f_elos
        df_sorted["o_ELO"] = o_elos

        elo_cols = df_sorted[["f_ELO", "o_ELO"]]
        self.fight_history_df = pd.concat(
            [self.fight_history_df.reset_index(drop=True), elo_cols.reset_index(drop=True)], axis=1
        )

    def _compute_survivor_score(self, df):
        KO_TKO_MULT = {1: 1.8, 2: 1.3, 3: 1.0, 4: 0.7, 5: 0.2}
        SUB_MULT    = {1: 1.2, 2: 1.2, 3: 0.8, 4: 0.5, 5: 0.1}

        df_sorted = df.sort_values("Date").reset_index(drop=True)
        scores = {}
        f_scores = [0.0] * len(df_sorted)
        o_scores = [0.0] * len(df_sorted)

        for i, row in df_sorted.iterrows():
            fighter  = row["Fighter"]
            opponent = row["Opponent"]
            method   = row["method"]
            winner   = row["winner"]
            rnd      = max(1, min(5, int(row["Round"]) if pd.notna(row["Round"]) else 3))

            f_score = scores.get(fighter,  1000.0)
            o_score = scores.get(opponent, 1000.0)
            f_scores[i] = f_score
            o_scores[i] = o_score

            win_name = winner if winner in (fighter, opponent) else None
            loser    = opponent if win_name == fighter else (fighter if win_name == opponent else None)

            if method == "KO/TKO":
                if win_name:
                    scores[win_name] = scores.get(win_name, 1000.0) + rnd * 10
                if loser:
                    scores[loser] = scores.get(loser, 1000.0) - 100 * KO_TKO_MULT.get(rnd, 1.0)
            elif method == "SUB":
                if win_name:
                    scores[win_name] = scores.get(win_name, 1000.0) + rnd * 10
                if loser:
                    scores[loser] = scores.get(loser, 1000.0) - 100 * SUB_MULT.get(rnd, 1.0)
            elif method == "DEC":
                scores[fighter]  = scores.get(fighter,  1000.0) + 100
                scores[opponent] = scores.get(opponent, 1000.0) + 100

        df_sorted["f_survivor_score"] = f_scores
        df_sorted["o_survivor_score"] = o_scores

        surv_cols = df_sorted[["f_survivor_score", "o_survivor_score"]]
        self.fight_history_df = pd.concat(
            [self.fight_history_df.reset_index(drop=True), surv_cols.reset_index(drop=True)], axis=1
        )

    def run_all(self):
        self.get_data()
        self.get_headers()
        self.set_dataframe()
        self.get_urls()
        self.set_dataframe_urls()
        self.find_fighter()
        self.get_fighter_info()
        self.set_fighthistory_dataframe()
        self.clean_data()
    
    def Display(self):
        return(self.dataframe_fighthistory)
    
to_scrape = 'abcdefgh'
for letter in to_scrape:
    scraper = DataExtraction(letter)
    scraper.scrape_page()  # saves to fighters_a.csv 