from bs4 import BeautifulSoup
import pandas as pd
import requests

class DataExtraction:
    def __init__(self, char):
        self.data = f'http://ufcstats.com/statistics/fighters?char={char.lower()}&page=all'
        self.char = char.lower()

    def get_data(self):
        page = requests.get(self.data)
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
        page = requests.get(url)
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
        page = requests.get(url)
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

    def get_fight_history(self, url, fighter_name):
        page = requests.get(url)
        soup = BeautifulSoup(page.text, 'html.parser')

        headers = [th.text.strip() for th in soup.find_all("th")]
        if not headers:
            return pd.DataFrame()
        headers.append("Date")

        event_idx = headers.index("Event") if "Event" in headers else None

        rows = []
        for tr in soup.find_all("tr"):
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
            if len(row) == len(headers) and any(v.strip() for v in row):
                rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows, columns=headers)
        df.insert(0, "Fighter_Name", fighter_name)
        return df

    def collect_all_fight_histories(self):
        all_dfs = []
        for i, url in enumerate(self.urls):
            try:
                row = self.dataframe.iloc[i]
                fighter_name = f"{row['First']} {row['Last']}".strip()
                df = self.get_fight_history(url, fighter_name)
                if not df.empty:
                    all_dfs.append(df)
            except Exception:
                pass
        if all_dfs:
            combined = pd.concat(all_dfs, ignore_index=True)
            dedup_cols = [c for c in ["Fighter", "Event", "Date"] if c in combined.columns]
            self.fight_history_df = combined.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
            self.clean_fight_history()
            self.compute_prefight_stats()
        else:
            self.fight_history_df = pd.DataFrame()

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
                       "Td_fighter", "Method", "fight_minutes", "Date"]].copy()
        forward.columns = ["name", "wl", "str_landed", "str_absorbed", "td", "method", "minutes", "date"]

        backward = df[["Opponent", "W/L", "Str_opponent", "Str_fighter",
                        "Td_opponent", "Method", "fight_minutes", "Date"]].copy()
        backward.columns = ["name", "wl", "str_landed", "str_absorbed", "td", "method", "minutes", "date"]
        backward["wl"] = backward["wl"].apply(
            lambda x: "L" if str(x).strip().lower() in ("w", "win")
            else ("W" if str(x).strip().lower() in ("l", "loss") else "D")
        )

        full_history = pd.concat([forward, backward], ignore_index=True).sort_values("date")

        def stats_for(name, before_date):
            prior = full_history[(full_history["name"] == name) & (full_history["date"] < before_date)]
            n = len(prior)
            if n == 0:
                return {k: 0.0 for k in ["SLpM", "SApM", "TD_pct", "W_pct", "KO_pct", "Sub_pct", "Finish_pct"]}
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
            }

        fighter_stats = df.apply(lambda row: stats_for(row["Fighter"], row["Date"]), axis=1)
        opponent_stats = df.apply(lambda row: stats_for(row["Opponent"], row["Date"]), axis=1)

        f_df = pd.DataFrame(fighter_stats.tolist()).add_prefix("f_")
        o_df = pd.DataFrame(opponent_stats.tolist()).add_prefix("o_")

        keep = ["W/L", "winner", "Date", "Fighter", "Opponent"]
        self.fight_history_df = pd.concat(
            [df[keep].reset_index(drop=True), f_df, o_df], axis=1
        )
        self._compute_elo(df)

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