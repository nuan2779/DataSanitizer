import os
import shutil
import pandas as pd
import numpy as np
from sklearn.datasets import load_iris

SAMPLES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "samples")
RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "raw")
os.makedirs(SAMPLES_DIR, exist_ok=True)

# 1. Melbourne Housing (copy from existing raw file)
melbourne_src = os.path.join(RAW_DIR, "92f7cba4-b9a5-4edd-b6da-57a0fe9b9b46.csv")
melbourne_dst = os.path.join(SAMPLES_DIR, "melbourne_housing.csv")
if os.path.exists(melbourne_src):
    shutil.copyfile(melbourne_src, melbourne_dst)
    print("1. Melbourne Housing copied successfully.")
else:
    # Look for any .csv in raw
    csvs = [f for f in os.listdir(RAW_DIR) if f.endswith(".csv")]
    if csvs:
        shutil.copyfile(os.path.join(RAW_DIR, csvs[0]), melbourne_dst)
        print("1. Melbourne Housing copied from fallback raw file.")

# 2. Iris Dataset (from sklearn)
iris_dst = os.path.join(SAMPLES_DIR, "iris.csv")
iris_data = load_iris(as_frame=True)
df_iris = iris_data.frame
# Rename columns cleanly
df_iris.columns = ["sepal_length", "sepal_width", "petal_length", "petal_width", "target"]
df_iris["species"] = df_iris["target"].map({0: "setosa", 1: "versicolor", 2: "virginica"})
df_iris.drop(columns=["target"], inplace=True)
df_iris.to_csv(iris_dst, index=False)
print(f"2. Iris dataset created ({len(df_iris)} rows).")

# 3. Titanic Dataset (standard realistic distribution)
np.random.seed(42)
n_titanic = 891
titanic_dst = os.path.join(SAMPLES_DIR, "titanic.csv")
pclass = np.random.choice([1, 2, 3], size=n_titanic, p=[0.24, 0.21, 0.55])
sex = np.random.choice(["male", "female"], size=n_titanic, p=[0.65, 0.35])
# Survival dependent on sex and pclass
prob_surv = np.where(sex == "female", 0.74, 0.19) - (pclass - 1) * 0.1
prob_surv = np.clip(prob_surv, 0.05, 0.95)
survived = (np.random.rand(n_titanic) < prob_surv).astype(int)

age = np.random.normal(loc=29.7, scale=14.5, size=n_titanic)
age = np.clip(age, 0.5, 80.0)
# inject ~20% missing values in Age
age[np.random.rand(n_titanic) < 0.2] = np.nan

sibsp = np.random.choice([0, 1, 2, 3, 4], size=n_titanic, p=[0.68, 0.23, 0.04, 0.03, 0.02])
parch = np.random.choice([0, 1, 2], size=n_titanic, p=[0.76, 0.13, 0.11])
fare = np.where(pclass == 1, np.random.exponential(60) + 25, 
                np.where(pclass == 2, np.random.exponential(20) + 10, np.random.exponential(10) + 5))
fare = np.round(fare, 2)
embarked = np.random.choice(["S", "C", "Q", None], size=n_titanic, p=[0.72, 0.19, 0.08, 0.01])

df_titanic = pd.DataFrame({
    "PassengerId": range(1, n_titanic + 1),
    "Survived": survived,
    "Pclass": pclass,
    "Name": [f"Passenger, Person {i}" for i in range(1, n_titanic + 1)],
    "Sex": sex,
    "Age": np.round(age, 1),
    "SibSp": sibsp,
    "Parch": parch,
    "Fare": fare,
    "Embarked": embarked
})
df_titanic.to_csv(titanic_dst, index=False)
print(f"3. Titanic dataset created ({len(df_titanic)} rows).")

# 4. Customer Churn Dataset (realistic telco dataset)
churn_dst = os.path.join(SAMPLES_DIR, "customer_churn.csv")
n_churn = 1000
gender = np.random.choice(["Male", "Female"], size=n_churn)
senior = np.random.choice([0, 1], size=n_churn, p=[0.84, 0.16])
partner = np.random.choice(["Yes", "No"], size=n_churn)
tenure = np.random.randint(1, 73, size=n_churn)
phone = np.random.choice(["Yes", "No"], size=n_churn, p=[0.9, 0.1])
internet = np.random.choice(["DSL", "Fiber optic", "No"], size=n_churn, p=[0.4, 0.45, 0.15])
contract = np.random.choice(["Month-to-month", "One year", "Two year"], size=n_churn, p=[0.55, 0.25, 0.2])
monthly_charges = np.where(internet == "Fiber optic", np.random.uniform(70, 110, size=n_churn),
                  np.where(internet == "DSL", np.random.uniform(40, 70, size=n_churn), np.random.uniform(18, 30, size=n_churn)))
monthly_charges = np.round(monthly_charges, 2)
total_charges = np.round(monthly_charges * tenure + np.random.normal(0, 5, size=n_churn), 2)
# inject small missing values
total_charges[np.random.rand(n_churn) < 0.01] = np.nan

prob_churn = np.where(contract == "Month-to-month", 0.4, 0.1) + np.where(tenure < 12, 0.2, 0.0)
prob_churn = np.clip(prob_churn, 0.05, 0.90)
churn = np.where(np.random.rand(n_churn) < prob_churn, "Yes", "No")

df_churn = pd.DataFrame({
    "customerID": [f"{np.random.randint(1000, 9999)}-{chr(65+i%26)}{chr(65+(i*3)%26)}" for i in range(n_churn)],
    "gender": gender,
    "SeniorCitizen": senior,
    "Partner": partner,
    "tenure": tenure,
    "PhoneService": phone,
    "InternetService": internet,
    "Contract": contract,
    "MonthlyCharges": monthly_charges,
    "TotalCharges": total_charges,
    "Churn": churn
})
df_churn.to_csv(churn_dst, index=False)
print(f"4. Customer Churn dataset created ({len(df_churn)} rows).")

print("All 4 sample datasets seeded into:", SAMPLES_DIR)
