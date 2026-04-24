import Data_Extraction_and_Cleaning as p1
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
import pandas as pd
from pydantic import BaseModel
from typing import Any

#dfurls = p1.info.clean_data()
dffh1 = p1.fighthistory1
#dffh2 = p1.fighthistory2

#convert all cells to int datatype from string
columns_to_convert_to_int = ["Kd_fighter", "Kd_opponent", "Str_fighter", "Str_opponent", "Td_fighter", "Td_opponent", "Round"]
for column in columns_to_convert_to_int:
    dffh1[column] = [int(char) for char in dffh1[column]]

#print(dffh1['Str_fighter'])
strikes_landed_per_minute = (dffh1['Round']*5)*float(p1.stats['SLpM'])
minutes = dffh1['Round']*5
dffh1['TIM'] = minutes
dffh1['SLPM'] = strikes_landed_per_minute
average_strikes = dffh1["Str_fighter"]/dffh1["Round"]
#print(average_strikes)
dffh1['avg_Str_fighter'] = average_strikes.reset_index(drop=True)
testing_data = {'Average_Strikes' : average_strikes}
print(testing_data)

class Visualize_Data(BaseModel):
    data : Any
    
    def create_double_bar_chart(self, column_title, df_cat1, df_cat2, topbar_label, bottombar_label):
        bar_chart = self.data.set_index(column_title).plot(kind='bar', y=[df_cat1, df_cat2], stacked=True, color=['#1f77b4', '#d62728'])
        top_bar = mpatches.Patch(color='#1f77b4', label=topbar_label)
        bottom_bar = mpatches.Patch(color='#d62728', label=bottombar_label)
        plt.legend(handles=[top_bar, bottom_bar])
        plt.setp(bar_chart.get_xticklabels(), rotation=45, ha='right')

    def create_scatterplot(self, x_data, y_data, title, x_label, y_label):
        scatterplot = sns.scatterplot(x = x_data, y = y_data, data = self.data)
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)

    def create_pairplot(self):
        pairplot = sns.pairplot(self.data, kind='scatter', plot_kws={'alpha': 0.4})
        
    def Display(self):
        plt.show()
        plt.close()


chart = Visualize_Data(data = dffh1)
#Enter column_title, y_val1, y_val2, topbar_label, bottombar_label
#bar_char = chart.create_double_bar_chart("Event", "Str_fighter", "Str_opponent", 'Fighter', 'Opponent')

#scatterplot = chart.create_scatterplot(dffh1["Round"], dffh1["Str_fighter"], "Total Strikes vs Number of Rounds", "Round", "Strikes")
#chart.create_pairplot()
#chart.Display()
sns.lmplot(y='Str_fighter', x='Round', data=dffh1, scatter_kws={'alpha' : 0.3})
plt.show()