import pandas as pd
import os

# --- CONFIGURATION ---
video_code = '01'
video_suffix = 'L' ### different angle have different offset, so we need to slice them separately
excel_path = f'./data/DataCollection_{video_code}.xlsx'  
offset_excel_path = './data/csv_offset.xlsx'  # Path to the new Excel file with offsets
csv_folder_path = './data/extracted_csv'  # Folder where CSV files for each video are stored
output_path = './output'  # Folder where sliced CSV files will be saved
video_folder_name = "25.1.20_01"

sheet_csv_map = {
    'Gaming Museum':   f'{video_code}_museum_3d_points.csv',
    'BowlingVR':       f'{video_code}_bowling_3d_points.csv',
    'Gallery of H.K. History': f'{video_code}_gallery_3d_points.csv',
    'Hong Kong Time Travel':   f'{video_code}_travel_3d_points.csv',
    'Boss Fight':      f'{video_code}_boss_3d_points.csv',
    'Candy Shooter':   f'{video_code}_candy_3d_points.csv',
}

# Path to your Excel file with cutting points
sheet_video_map = {
    'Gaming Museum':   f'{video_code}_museum_{video_suffix}.mp4',
    'BowlingVR':       f'{video_code}_bowling_{video_suffix}.mp4',
    'Gallery of H.K. History': f'{video_code}_gallery_{video_suffix}.mp4',
    'Hong Kong Time Travel':   f'{video_code}_travel_{video_suffix}.mp4',
    'Boss Fight':      f'{video_code}_boss_{video_suffix}.mp4',
    'Candy Shooter':   f'{video_code}_candy_{video_suffix}.mp4'
}

# --- Function to Slice CSV Based on Frame Ranges and Offsets ---
def slice_csv_based_on_offsets(csv_path, sheet_name, offset_df, data_collection_path,output_path):  # Create output directory if it doesn't exist:
    
    # --- read the offset data for the current sheet ---
    video_name = sheet_video_map[sheet_name]
    matched_row = offset_df[offset_df['video_name'] == video_name]  # Get the video name from the mapping
    if matched_row.empty:
        print(f"No offset data found for {video_name}. Skipping...")
        return
    offset_value = matched_row['offset'].values[0]  # Get the offset value for this video
    
    # --- Extract relevant frame range information from the Data Collection Excel ---
    df = pd.read_excel(data_collection_path, sheet_name=sheet_name)
    rep_start_cols = [col for col in df.columns if 'Repetition' in col and 'Start' in col]
    rep_end_cols = [col for col in df.columns if 'Repetition' in col and 'End' in col]

    # Read the extracted 3D points CSV
    csv_data = pd.read_csv(csv_path)
    
    

    # --- Iterate over each repetition and slice the CSV accordingly ---
    for row_idx, row in df.iterrows():
        for rep in range(1, len(rep_start_cols) + 1):
            start_col = f"Repetition {rep} Start"
            end_col = f"Repetition {rep} End"

            start_frame = row.get(start_col)
            end_frame = row.get(end_col)


            if pd.notna(start_frame) and pd.notna(end_frame):
            
                # Apply offset and slice the data
                start_frame += offset_value
                end_frame += offset_value
                
                # Slice the data based on start_frame and end_frame
                if start_frame < 0:
                    start_frame = 0  # To prevent slicing below 0

                sliced_csv = csv_data.iloc[int(start_frame):int(end_frame)]

                # Create a filename for the sliced CSV
                output_csv_dir = output_path + '/' + 'CSV_' + video_name[:-4] ## Remove the file extension from the video name
                output_csv_path = os.path.join(output_csv_dir, f"csv_{video_name[:-4]}_{row_idx+1}_rep{rep}.csv")
                os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)
                
                # Save the sliced CSV
                sliced_csv.to_csv(output_csv_path, index=False)
                print(f"Sliced CSV saved: {output_csv_path}")


# --- Load the Offset Excel and Data Collection Excel ---
offset_df = pd.read_excel(offset_excel_path, sheet_name=video_folder_name )

# --- Iterate over each sheet and process the corresponding CSV file ---
for sheet_name, csv_name in sheet_csv_map.items():
    csv_path = csv_folder_path + '/' + csv_name
    slice_csv_based_on_offsets(csv_path, sheet_name, offset_df, excel_path, output_path)
