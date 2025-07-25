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

for row in cursor.execute(query2):
    print(f"Forme juridique: {row[0]}, pourcentage: {row[1]:.2f}%")
print('\n')


# percentage of companies per NACE code
query3 = """
    WITH filtered_activity AS (
        SELECT EntityNumber, NaceCode, NaceVersion
        FROM activity
        WHERE Classification = 'MAIN'
    ),
    valid_codes AS (
        SELECT Category, Code, Description
        FROM code
        WHERE Language = 'FR'
        AND Category IN ('NACE2025', 'NACE2008', 'NACE2003')
    )
    SELECT
        vc.Description,
        COUNT(DISTINCT fa.EntityNumber) * 100.0 / (
            SELECT COUNT(*) FROM enterprise WHERE JuridicalForm IS NOT NULL
        ) AS percentage
    FROM
        filtered_activity fa
    JOIN
        valid_codes vc
        ON CAST(fa.NaceCode AS TEXT) = vc.Code
        AND (
            (fa.NaceVersion = 2025 AND vc.Category = 'NACE2025') OR
            (fa.NaceVersion = 2008 AND vc.Category = 'NACE2008') OR
            (fa.NaceVersion = 2003 AND vc.Category = 'NACE2003')
        )
    GROUP BY
        vc.Description
    ORDER BY
        percentage DESC
    LIMIT 10;
"""

for row in cursor.execute(query3):
    print(f"Secteur d'activité: {row[0]}, pourcentage: {row[1]:.2f}%")
print('\n')



from collections import defaultdict

# Initialiser les totaux par région
region_percentages = defaultdict(float)

# Mapping regions by Zipcode
def map_postcode_to_region(Zipcode):
    try:
        pc = int(Zipcode)
        if 1000 <= pc <= 1299:
            return "Brussels"
        elif (1300 <= pc <= 1499) or (4000 <= pc <= 7999):
            return "Wallonia"
        elif 1500 <= pc <= 3999:
            return "Flanders"
        else:
            return "Unknown"
    except:
        return "Unknown"
    
# percentage of companies per region
query4 = f"""
SELECT
    Zipcode,
    COUNT(*) * 100.0 / (SELECT COUNT(*) FROM address WHERE Zipcode IS NOT NULL) AS percentage
FROM
    address
WHERE
    Zipcode IS NOT NULL
GROUP BY
    Zipcode
ORDER BY
    percentage DESC;
"""

# Agrégation des pourcentages par région
for row in cursor.execute(query4):
    region = map_postcode_to_region(row[0])
    region_percentages[region] += row[1]

# Affichage final trié
for region, pct in sorted(region_percentages.items(), key=lambda x: -x[1]):
    print(f"Région: {region}, Pourcentage of Companies: {pct:.2f}%")
print('\n')


