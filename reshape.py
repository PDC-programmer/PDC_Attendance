import pandas as pd

# Load the Excel file
df = pd.read_excel("reshaped_leave_data.xlsx")

# Prepare columns for reshaped DataFrame
columns = ["staff_code", "total_hours", "remaining_hours", "leave_type_id"]
reshaped_data = []

# Start leave_type_id from 1
leave_type_id = 1

# Iterate over columns to reshape data
for col_idx in range(1, len(df.columns), 2):  # Assuming 'total_hours' and 'remaining_hours' are consecutive
    staff_code = df.iloc[:, 0]  # Assuming the first column is 'staff_code'
    total_hours = df.iloc[:, col_idx]
    remaining_hours = df.iloc[:, col_idx + 1]

    # Add reshaped data to the list
    for i in range(len(df)):
        reshaped_data.append([
            staff_code.iloc[i],
            total_hours.iloc[i],
            remaining_hours.iloc[i],
            leave_type_id
        ])

    # Increment leave_type_id for the next leave type
    leave_type_id += 1

# Create the reshaped DataFrame
df_reshaped = pd.DataFrame(reshaped_data, columns=columns)

# Display the reshaped DataFrame
df_reshaped.to_excel("final_reshaped_leave_data.xlsx", index=False)

print("Reshaping complete. Data saved to 'final_reshaped_leave_data.xlsx'.")
