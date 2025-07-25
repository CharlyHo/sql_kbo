import matplotlib.pyplot as plt
import geopandas as gpd
from collections import defaultdict
import pandas as pd
import os
import sqlite3

connexion = sqlite3.connect("kbo_database.db")
cursor = connexion.cursor()

# Count the number of companies in the database
query1 = f"""
    SELECT
        count(distinct(activity.EntityNumber))
    FROM
        activity;
"""

for row in cursor.execute(query1):
    print("Number of Companies: ", row[0])


# test  nb companies nonNULL juridicForm
query1ter = f"""
    SELECT
        count(distinct(EnterpriseNumber))
    FROM
        enterprise
    WHERE
        JuridicalForm IS NOT NULL;
"""

for row in cursor.execute(query1ter):
    print("Number of Companies: ", row[0])



# nb of distinct juridical forms
query1bis = f"""
    SELECT
        count(distinct(JuridicalForm))
    FROM
        enterprise
    WHERE
        JuridicalForm IS NOT NULL;
"""

for row in cursor.execute(query1bis):
    print("Number of Juridical Forms: ", row[0], '\n')



# percentage of companies per juridical form
query2 = f"""
    SELECT
        code.Description,
        COUNT(*) * 100.0 / (SELECT COUNT(*) FROM enterprise WHERE JuridicalForm IS NOT NULL) AS percentage
    FROM
        enterprise
    JOIN
        code ON enterprise.JuridicalForm = code.Code
    WHERE
        code.Category = 'JuridicalForm' AND
        code.Language = 'FR'
    GROUP BY
        code.Description
    ORDER BY
        percentage DESC
    LIMIT 10;
"""

# Exécuter la requête et stocker les résultats
descriptions = []
percentages = []

for row in cursor.execute(query2):
    descriptions.append(row[0])
    percentages.append(row[1])

# Créer le graphique
plt.figure(figsize=(10, 6))
bars = plt.barh(descriptions, percentages, color='skyblue')
plt.xlabel("Percentage (%)")
plt.title("Top 10 of juridical forms in companies in Belgium")
plt.gca().invert_yaxis()
plt.tight_layout()

# Annoter les barres
for bar in bars:
    width = bar.get_width()
    plt.text(width + 0.5, bar.get_y() + bar.get_height()/2, f"{width:.2f}%", va='center')

# Sauvegarder le graphique
plt.savefig("top10_juridical_forms.png", dpi=300, bbox_inches="tight")
plt.show()


# percentage of companies per NACE code
query3 = """
    SELECT 
        vc.Description,
        COUNT(DISTINCT fa.EntityNumber) * 100.0 / (
            SELECT COUNT(*) FROM enterprise WHERE JuridicalForm IS NOT NULL
        ) AS percentage
    FROM 
        activity fa
    JOIN 
        code vc ON CAST(fa.NaceCode AS TEXT) = vc.Code
    WHERE 
        fa.Classification = 'MAIN'
        AND vc.Language = 'FR'
    GROUP BY 
        vc.Description
    ORDER BY 
        percentage DESC
    LIMIT 10;
"""

for row in cursor.execute(query3):
    results = cursor.fetchall()

# Séparer les labels et valeurs
labels = [row[0] for row in results]
percentages = [row[1] for row in results]

# Taille du graphique
plt.figure(figsize=(12, 6))

# Bar chart horizontal
bars = plt.barh(labels, percentages, color='skyblue')
plt.xlabel("Pourcentage des entreprises (%)")
plt.title("Top 10 des secteurs d'activité principaux (NACE)")
plt.gca().invert_yaxis()

# Ajouter les valeurs au bout des barres
for bar in bars:
    width = bar.get_width()
    plt.text(width + 0.2, bar.get_y() + bar.get_height()/2,
             f"{width:.2f}%", va='center')

plt.tight_layout()
plt.savefig("top_10_nace.png", dpi=300, bbox_inches='tight')
plt.show()





# Requète pour voir la repartition géographique des entreprises par région
region_percentages = defaultdict(float)
query4 = """
    SELECT
        Zipcode,
        COUNT(*) * 100.0 / (SELECT COUNT(*) FROM address WHERE Zipcode IS NOT NULL) AS percentage
    FROM
        address
    WHERE
        Zipcode IS NOT NULL
    GROUP BY
        Zipcode;
"""

# mapping des régions
def map_postcode_to_region(pc):
    try:
        pc = int(pc)
        if 1000 <= pc <= 1299:
            return "Brussels"
        elif (1300 <= pc <= 1499) or (4000 <= pc <= 7999):
            return "Wallonia"
        elif 1500 <= pc <= 3999:
            return "Flanders"
    except:
        pass
    return "Not in Belgium"

for zipcode, pct in cursor.execute(query4):
    region_percentages[map_postcode_to_region(zipcode)] += pct

print(region_percentages)

# Charger le GeoJSON régions Belgique
geojson_path = "belgium_regions.json"
gdf = gpd.read_file(geojson_path)

# Préparer les données pour la jointure
mapping_id = {
    "Brussels": "BEBRU",
    "Flanders": "BEVLG",
    "Wallonia": "BEWAL"
}

# Ajouter la colonne percentage au GeoDataFrame
gdf["percentage"] = gdf["id"].map({
    mapping_id[k]: v for k, v in region_percentages.items() if k in mapping_id
})

# Tracer la carte
fig, ax = plt.subplots(figsize=(8, 6))
gdf.plot(column="percentage",
         cmap="OrRd", 
         legend=True, 
         legend_kwds={'label': "Pourcentage d'entreprises (%)"},
         edgecolor='black',
         ax=ax)

ax.set_title("Répartition des entreprises par région (Belgique)")
ax.axis("off")

# Sauvegarder et afficher
plt.tight_layout()
plt.savefig("belgium_companies_by_region.png", dpi=300, bbox_inches='tight')
plt.show()




# Requète pour afficher la répartition geo en fonction des Codes NACE wellness
query5 = """
SELECT a.Zipcode
FROM activity act
JOIN address a ON act.EntityNumber = a.EntityNumber
WHERE act.NaceCode = ?
AND a.Zipcode IS NOT NULL
"""

params = ('9604003',)

# Fonction pour mapper les codes postaux aux régions
region_counts = defaultdict(int)
total = 0

for (zipcode,) in cursor.execute(query5, params):
    region = map_postcode_to_region(zipcode)
    region_counts[region] += 1
    total += 1

connexion.close()


region_percentages = {
    region: (count / total) * 100
    for region, count in region_counts.items()
    if region != "Not in Belgium"  # facultatif
}

print("Répartition % par région :", region_percentages)

# Charger GeoJSON des régions
gdf = gpd.read_file("belgium_regions.json")

# Convertir en DataFrame pour fusion
df_pct = pd.DataFrame(list(region_percentages.items()), columns=['region', 'percentage'])

# Fusionner avec la carte
gdf = gdf.merge(df_pct, left_on='name', right_on='region', how='left')

# Remplacer les NaN par 0
gdf['percentage'] = gdf['percentage'].fillna(0)

# Tracer la carte
fig, ax = plt.subplots(1, 1, figsize=(10, 8))
gdf.plot(column='percentage', ax=ax, cmap='OrRd', edgecolor='black', legend=True)

plt.title("Répartition % des entreprises Wellness (NACE 9604003) par région")
plt.axis('off')
plt.savefig("wellness_repartition_by_region.png", dpi=300, bbox_inches='tight')
plt.show()
