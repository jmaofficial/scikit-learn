import pandas as pd
import matplotlib.pyplot as plt

# 1. Read the raw data
df = pd.read_csv("changecoupling.csv")
data = []

# 2. Clean the squished file paths
for _, row in df.iterrows():
    entities = row['coupled entities']
    
    # Split the string where the two file paths merged
    if '.pyscikit-learn/' in entities:
        file1, file2_part = entities.split('.pyscikit-learn/', 1)
        file1 += '.py'
        file2 = 'scikit-learn/' + file2_part
    else:
        file1 = entities
        file2 = "UNKNOWN"
        
    data.append({
        'Production Code': file1, 
        'Test Code': file2, 
        'Coupling %': row['degree  of coupling'], 
        'Commits': row['average revision']
    })

df_clean = pd.DataFrame(data)

# 3. Filter for Production/Test pairs (one file has 'test' in the name, the other doesn't)
def is_test(filename):
    return 'test' in filename.lower()

prod_test_pairs = []
for _, row in df_clean.iterrows():
    f1_test = is_test(row['Production Code'])
    f2_test = is_test(row['Test Code'])
    
    # We only want pairs where EXACTLY one is a test file
    if (f1_test and not f2_test):
        prod_test_pairs.append({'Production Code': row['Test Code'], 'Test Code': row['Production Code'], 'Coupling %': row['Coupling %'], 'Commits': row['Commits']})
    elif (not f1_test and f2_test):
        prod_test_pairs.append(row)

df_final = pd.DataFrame(prod_test_pairs)

# 4. Print the results for the report
print(df_final.sort_values(by='Commits', ascending=False).to_string(index=False))