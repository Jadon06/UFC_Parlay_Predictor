from bs4 import BeautifulSoup
import pandas as pd
import requests

# fighter1 = input("Enter a fighter: ").title().strip()
# last_name_initial1 = fighter1.split(" ", 1)[1][0].lower()

#fighter2 = input("Enter a fighter: ").title().strip()
#last_name_initial2 = fighter2.split(" ", 1)[1][0].lower()

# All_fighters_inital1 = 'http://ufcstats.com/statistics/fighters?char='+last_name_initial1+'&page=all'
#All_fighters_inital2 = 'http://ufcstats.com/statistics/fighters?char='+last_name_initial2+'&page=all'

class FighterInfo:
    def __init__(self, fighter):
        if fighter == "NA":
            return None
        self.data = f'http://ufcstats.com/statistics/fighters?char={fighter.split(" ", 1)[1][0].lower()}&page=all'
        self.fighter = fighter
        #self.fighter2 = fighter2

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

    def find_fighter(self):
        fighter_name_fixed = self.fighter.title().strip()
        fighter_split_name = self.fighter.split(" ")
        
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
            fighters_link = 'http://ufcstats.com/statistics/fighters?char='+last_name_initials[i]+'&page=all'
            fighter = FighterInfo(fighters_link, opponents[i])
            fighter.get_data()
            fighter.get_headers()
            fighter.set_dataframe()
            fighter.get_urls()
            fighter.set_dataframe_urls()
            temp_df = fighter.find_fighter()
            stance = temp_df['Stance'].iloc[0]
            stances.append(stance)
        stance_df["Stance"] = stances
        return(stance_df)
    
    def get_career_stats(self):
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
        stats = dict(zip(keys, values))
        return stats


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
    

# F1_info = FighterInfo(All_fighters_inital1, fighter1)
# F1_info.run_all()
# stats = F1_info.get_career_stats()
# fighthistory1 = F1_info.Display()
# #found = F1_info.find_fighter()
# #print(found)
# print(fighthistory1)

# #F2_info = FighterInfo(All_fighters_inital2, fighter2)
# #F2_info.run_all()
# #fighthistory2 = F2_info.set_dataframe_urls()
# #print(fighthistory2)
    
# test = FighterInfo("Daniel Cormier")
# test.run_all()
# print(test.Display())

#df = test.get_opponents_stance()
#print(df)