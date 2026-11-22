import pandas as pd

#Récupération des données
df = pd.read_csv('/home/onyxia/work/Data/Raw/frequentation-gares.csv', sep=";")

#df.shape
#df.head()
#df.info()
#print(df.describe())
#print(df.duplicated().sum())

#Restructuration
columns_drop=[col for col in df.columns if "+ Non" in col]
#print(columns_drop)
df=df.drop(columns_drop, axis=1) #suppression des données non voyageus
#print(df.info())
#print(df.head())

id_vars=[df.columns[i] for i in range(6)]
#print(id_vars)
value_vars=[df.columns[i] for i in range(7,17)]
#print(value_vars)
df_long = df.melt(id_vars= id_vars, value_vars= value_vars, var_name = "indicateur année", value_name= "fréquentation") #passage au format long
df_long["année"]=df_long["indicateur année"].str[-4:]
df_long=df_long.drop("indicateur année", axis=1) #Ajout de la colonne année
cols = list(df_long.columns)
col = cols.pop(-1)
cols.insert(-1, col)
df_long = df_long[cols] #Repositionne colonne année
#print(df_long.info())
#print(df_long.head())

df_long.to_csv("Data/Clean/frequentation-gares.csv")
#Valeurs manquantes

#print((df_long["fréquentation"] == 0).sum())
#print((df_long["fréquentation"] == 0).mean() * 100)
#gares_zero = (df_long[df_long["fréquentation"] == 0].groupby("Code UIC").agg(nb_annees_zero=("année", "count"),premiere_annee_zero=("année", "min"),derniere_annee_zero=("année", "max")).reset_index())
#print(gares_zero)
#gares_zero.to_excel("gares_zero.xlsx", index=False)
#print(pd.crosstab(df_long["Segmentation DRG"],df_long["fréquentation"].eq(0),normalize="index") * 100)