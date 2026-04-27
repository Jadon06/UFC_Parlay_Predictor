from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
import math
import pandas as pd
import requests


class FighterInfo:
    _HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    def __init__(self, fighter1, fighter2):
        self.fighter1 = fighter1
        self.fighter2 = fighter2

    def _map_method(self, method_str):
        m = str(method_str).strip().upper()
        if "DECISION" in m or m in ("U-DEC", "S-DEC", "M-DEC"):
            return "DEC"
        if "KO" in m or "TKO" in m:
            return "KO/TKO"
        if "SUBMISSION" in m or "SUB" in m:
            return "SUB"
        return "other"

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

    def _find_fighter_url(self, fighter_name):
        data_url = f'http://ufcstats.com/statistics/fighters?char={fighter_name.split(" ", 1)[1][0].lower()}&page=all'
        page = requests.get(data_url, headers=self._HEADERS)
        soup = BeautifulSoup(page.text, 'html.parser')
        row_data = soup.find_all("tr")

        table_headers = [th.text.strip() for th in soup.find_all("th")]
        dataframe = pd.DataFrame(columns=table_headers)

        urls = []
        for row in row_data:
            cell_data = row.find_all("td")
            row_info = [data.text.strip() for data in cell_data]
            try:
                dataframe.loc[len(dataframe)] = row_info
            except ValueError:
                pass
            for tag in cell_data:
                ref = tag.find('a')
                if ref:
                    urls.append(ref['href'])
        urls = [link for i, link in enumerate(urls) if link not in urls[:i]]
        urls = [u for u in urls if u]
        dataframe['UFC Link'] = urls

        parts = fighter_name.split(" ")
        mask = (dataframe['First'] == parts[0]) & (dataframe['Last'] == " ".join(parts[1:]))
        index = dataframe.index[mask]
        links = list(dataframe.loc[index, 'UFC Link'])
        return links[0] if links else None

    def _scrape_fight_history(self, fighter_url):
        page = requests.get(fighter_url, headers=self._HEADERS)
        soup = BeautifulSoup(page.text, 'html.parser')

        headers = [th.text.strip() for th in soup.find_all("th")]
        if not headers:
            return pd.DataFrame()
        headers += ["Date", "f_ctrl", "o_ctrl"]

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
            row += [f_ctrl, o_ctrl]
            if len(row) == len(headers) and any(v.strip() for v in row):
                rows.append(row)

        return pd.DataFrame(rows, columns=headers) if rows else pd.DataFrame()

    def _compute_stats_from_history(self, df):
        if df.empty:
            return {}

        df[["Td_fighter", "Td_opponent"]] = df["Td"].astype(str).str.split(" ", expand=True)
        df[["Str_fighter", "Str_opponent"]] = df["Str"].astype(str).str.split(" ", expand=True)

        split_names = df["Fighter"].astype(str).str.split(" ", expand=True)
        df["Fighter"]  = split_names.loc[:, 0:1].apply(lambda r: " ".join(r.dropna()), axis=1)
        df["Opponent"] = split_names.loc[:, 2:].apply(lambda r: " ".join(r.dropna()), axis=1)

        df["method"] = df["Method"].apply(self._map_method)
        df["is_win"]  = df["W/L"].str.strip().str.lower().isin(["w", "win"])

        for col in ["Str_fighter", "Str_opponent", "Td_fighter", "Round"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        df["Date"] = pd.to_datetime(df["Date"], format="mixed", errors="coerce")
        df = df.sort_values("Date").reset_index(drop=True)

        def ctrl_to_seconds(val):
            try:
                parts = str(val).strip().split(":")
                return int(parts[0]) * 60 + int(parts[1])
            except Exception:
                return 0.0

        df["ctrl_sec"] = df["f_ctrl"].apply(ctrl_to_seconds)

        def parse_minutes(row):
            try:
                parts = str(row["Time"]).strip().split(":")
                return (row["Round"] - 1) * 5 + int(parts[0]) + int(parts[1]) / 60
            except Exception:
                return row["Round"] * 5

        df["fight_minutes"] = df.apply(parse_minutes, axis=1)

        n         = len(df)
        total_min = df["fight_minutes"].sum() or 1
        wins      = df[df["is_win"]]
        n_wins    = len(wins)
        last5     = df.tail(5)
        ko_wins   = wins["method"].str.contains("KO/TKO", case=False, na=False).sum()
        sub_wins  = wins["method"].str.contains("SUB",    case=False, na=False).sum()
        finishes  = (~df["method"].str.contains("DEC",   case=False, na=False)).sum()

        stats = {
            "SLpM":       round(df["Str_fighter"].sum() / total_min, 3),
            "SApM":       round(df["Str_opponent"].sum() / total_min, 3),
            "TD_pct":     round(df["Td_fighter"].sum() / n, 3),
            "W_pct":      round(last5["is_win"].sum() / len(last5), 3),
            "KO_pct":     round(ko_wins  / max(n_wins, 1), 3),
            "Sub_pct":    round(sub_wins / max(n_wins, 1), 3),
            "Finish_pct": round(finishes / n, 3),
            "ctrl":       round(df["ctrl_sec"].mean(), 3),
        }

        # ELO — opponent assumed 1000 each fight (only this fighter's history available)
        elo = 1000.0
        for _, row in df.iterrows():
            opp_elo = 1000.0
            diff    = abs(elo - opp_elo)
            if diff == 0:
                change = elo * 0.008
            elif diff <= 30:
                change = diff
            elif diff <= 100:
                change = math.ceil(diff * 0.7)
            else:
                change = diff * 0.07
            elo += change if row["is_win"] else -change
        stats["ELO"] = round(elo, 3)

        # Survivor score
        KO_TKO_MULT = {1: 1.8, 2: 1.3, 3: 1.0, 4: 0.7, 5: 0.2}
        SUB_MULT    = {1: 1.2, 2: 1.2, 3: 0.8, 4: 0.5, 5: 0.1}
        survivor = 1000.0
        for _, row in df.iterrows():
            method = row["method"]
            rnd    = max(1, min(5, int(row["Round"]) if pd.notna(row["Round"]) else 3))
            if method == "KO/TKO":
                survivor += rnd * 10 if row["is_win"] else -100 * KO_TKO_MULT.get(rnd, 1.0)
            elif method == "SUB":
                survivor += rnd * 10 if row["is_win"] else -100 * SUB_MULT.get(rnd, 1.0)
            elif method == "DEC":
                survivor += 100
        stats["survivor_score"] = round(survivor, 3)

        return stats

    def _get_fighter_stats(self, fighter_name):
        url = self._find_fighter_url(fighter_name)
        if not url:
            return {}
        df = self._scrape_fight_history(url)
        return self._compute_stats_from_history(df)

    def get_prediction_row(self):
        with ThreadPoolExecutor(max_workers=2) as ex:
            f1_future = ex.submit(self._get_fighter_stats, self.fighter1)
            f2_future = ex.submit(self._get_fighter_stats, self.fighter2)
            f1_stats  = f1_future.result()
            f2_stats  = f2_future.result()

        stat_keys = ["SLpM", "SApM", "TD_pct", "W_pct", "KO_pct", "Sub_pct", "Finish_pct", "ctrl", "ELO", "survivor_score"]
        row = {"Fighter": self.fighter1, "Opponent": self.fighter2}
        row.update({f"f_{k}": f1_stats.get(k, 0) for k in stat_keys})
        row.update({f"o_{k}": f2_stats.get(k, 0) for k in stat_keys})

        df = pd.DataFrame([row])
        df["SLpM_diff"]  = df["f_SLpM"]       - df["o_SLpM"]
        df["SApM_diff"]  = df["f_SApM"]       - df["o_SApM"]
        df["TD_diff"]    = df["f_TD_pct"]     - df["o_TD_pct"]
        df["KO_diff"]    = df["f_KO_pct"]     - df["o_KO_pct"]
        df["Sub_diff"]   = df["f_Sub_pct"]    - df["o_Sub_pct"]
        df["Fin_diff"]   = df["f_Finish_pct"] - df["o_Finish_pct"]
        df["ELO_diff"]   = df["f_ELO"]        - df["o_ELO"]
        return df
