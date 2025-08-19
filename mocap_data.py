import numpy as np
import pandas as pd
from PyQt5.QtWidgets import QProgressDialog, QMessageBox
from PyQt5.QtCore import QCoreApplication

class RawMocapData:
    def __init__(self, df, type_list):
        """
        Initialize the RawMocapData object.

        :param df: The pandas DataFrame containing the 3D data.
        :param type_list: List of column types from the DataFrame. This list should ideally correspond to df.columns.
        """
        
        # Determine which columns to keep based on having at least 100 non-empty data points
        columns_to_keep = []
        original_column_names = df.columns.tolist()

        threshold = 600
        
        for col_name_from_df in original_column_names:
            series = df[col_name_from_df]
            if series.dtype == 'object':
                # For object type, count non-null and non-empty strings as valid
                valid_count = series.dropna().astype(str).str.strip().replace('', np.nan).dropna().count()
            else:
                # For numeric types, just count non-null values
                valid_count = series.count() # pandas .count() excludes NaN

            if valid_count >= threshold:
                columns_to_keep.append(col_name_from_df)
        
        if len(columns_to_keep) < len(original_column_names):
            dropped_columns = set(original_column_names) - set(columns_to_keep)
            print(f"Dropping {len(dropped_columns)} empty columns because they have less than {threshold} valid data points.")
            df_filtered = df[columns_to_keep] # Create a new DataFrame with only the desired columns
            filtered_type_list = columns_to_keep # Update type_list to reflect the kept columns
        else:
            df_filtered = df
            filtered_type_list = type_list # No columns dropped, use the original type_list
        
        self.total_frames = len(df_filtered)
        print(f"loaded {self.total_frames} frames.")

        # Group columns and get sorted joint names and original df column indices
        self._sorted_joint_names, original_df_col_indices, self._joint_name_to_indices = self._group_columns(filtered_type_list)
        
        # Reshape data into [T, N, 3] NumPy array
        self.num_raw_joints = len(self._sorted_joint_names) # N is the number of included joints
        self.data_array = np.zeros((self.total_frames, self.num_raw_joints, 3), dtype=float)

        for n_idx, (x_col_idx, y_col_idx, z_col_idx) in enumerate(original_df_col_indices):
            self.data_array[:, n_idx, 0] = df_filtered.iloc[:, x_col_idx].values
            self.data_array[:, n_idx, 1] = df_filtered.iloc[:, y_col_idx].values
            self.data_array[:, n_idx, 2] = df_filtered.iloc[:, z_col_idx].values
        
        # Replace NaN values with 0.0
        self.data_array = np.nan_to_num(self.data_array, nan=0.0)

        print(f"Reshaped data to {self.data_array.shape} (Frames, Joints, XYZ).")
        print(f"Number of raw joints identified: {self.num_raw_joints}")

    
    def get_total_frame(self):
        return self.total_frames
    
    def get_joint_names(self):
        """
        Get the sorted list of joint names.
        :return: A list of sorted joint names.
        """
        return self._sorted_joint_names
    
    def get_joint_indices(self, joint_name):
        """
        Get the index of a specific joint name in the reshaped data array's joint dimension.
        :param joint_name: The name of the joint (e.g., "1:Skeleton 001:Hip(Bone)").
        :return: The integer index of the joint, or None if not found.
        """
        return self._joint_name_to_indices.get(joint_name)
    
    def _group_columns(self, type_list):
        """
        Groups columns by joint name and prepares data for reshaping.
        Sorts joint names and creates mappings to their indices in the reshaped array.

        :param type_list: List of column names from the DataFrame.
        :return: A tuple containing (sorted_joint_names, original_df_col_indices, joint_name_to_data_array_index).
                 - sorted_joint_names: List of unique joint base names, sorted.
                 - original_df_col_indices: List of (X, Y, Z) column indices from the original DataFrame,
                                            corresponding to the sorted joint names.
                 - joint_name_to_data_array_index: Dictionary mapping joint base names to their
                                                   index in the reshaped data_array's joint dimension.
        """
        grouped_cols = {}
        for i, col_name in enumerate(type_list):
            if col_name.endswith('_X'):
                base_name = col_name[:-2]
                grouped_cols.setdefault(base_name, {})['X'] = i
            elif col_name.endswith('_Y'):
                base_name = col_name[:-2]
                grouped_cols.setdefault(base_name, {})['Y'] = i
            elif col_name.endswith('_Z'):
                base_name = col_name[:-2]
                grouped_cols.setdefault(base_name, {})['Z'] = i
        
        # Define sorting key function for joint names
        def sort_key_func(name):
            # Extract the prefix of the name (e.g., "Skeleton 001", "WandTracker", "Unlabeled")
            # This assumes the format is "{id}:{Prefix} {Number}:{Name}({Type})" or similar
            parts = name.split(':')
            if len(parts) > 1:
                name_part = parts[1].strip()
                if ' ' in name_part:
                    prefix = name_part.split(' ')[0]
                else:
                    prefix = name_part # In case it's just a single word like "Unlabeled"
            else:
                prefix = ""
            
            # Extract the ID part
            id_part = parts[0]

            # Priority 1: "Skeleton 001" prefix comes first
            if "Skeleton" in prefix: # Check for "Skeleton" as a broader category for 001, etc.
                prefix_priority = 0
            elif "Unlabeled" in prefix:
                prefix_priority = 2
            else:
                prefix_priority = 1 # Other prefixes like "WandTracker" go in between

            # Priority 2: Sort by ID within the same prefix priority
            if id_part.isdigit():
                return (prefix_priority, 0, int(id_part))  # Numeric IDs come first, sorted by integer value
            else:
                return (prefix_priority, 1, id_part)      # Non-numeric IDs come second, sorted by string value

        # Sort joint names using the defined key
        sorted_joint_names = sorted(grouped_cols.keys(), key=sort_key_func)
        
        original_df_col_indices = [] # Stores original df column indices for X, Y, Z for reshaping
        joint_name_to_data_array_index = {} # Maps joint name to its new index in the N dimension of data_array
        
        current_n_idx = 0
        for joint_name in sorted_joint_names:
            coords = grouped_cols[joint_name]
            if 'X' in coords and 'Y' in coords and 'Z' in coords:
                original_df_col_indices.append((coords['X'], coords['Y'], coords['Z']))
                joint_name_to_data_array_index[joint_name] = current_n_idx
                current_n_idx += 1
            else:
                print(f"Warning: {joint_name} does not have all X, Y, Z coordinates. Skipping for reshape.")

        return sorted_joint_names, original_df_col_indices, joint_name_to_data_array_index

    def __getitem__(self, frame):
        """
        Get the 3D data for a specific frame.
        :param frame: Frame index.
        :return: 3D data for the frame in [N, 3] (Joints, XYZ) format.
        """
        if frame < 0 or frame >= self.total_frames:
            raise IndexError("Frame index out of range.")
        return self.data_array[frame]

    def get_joints_by_names(self, frame, joint_name_list):
        """
        根據 frame index 和 joint 名稱 list 回傳對應的 3D 資料（[N,3]）。
        :param frame: 幀索引
        :param joint_name_list: 關節名稱 list
        :return: shape = (len(joint_name_list), 3) 的 numpy array
        """
        indices = [self._joint_name_to_indices[name] for name in joint_name_list if name in self._joint_name_to_indices]
        return self.data_array[frame, indices, :] if indices else np.zeros((0,3))