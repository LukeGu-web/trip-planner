import pandas as pd
import json
from pathlib import Path

def generate_distance_map():
    # Read Excel file
    df = pd.read_excel('open-data-opal-distance-tables-2024-12.xlsx', sheet_name='Rail')
    
    # Create distance mapping dictionary
    distance_map = {}
    
    # Get all station names (starting from column 4)
    stations = df.columns[3:].tolist()
    
    # Iterate through each row
    for _, row in df.iterrows():
        origin = row['Rail Distances (over the track) in km']
        if pd.isna(origin) or not isinstance(origin, str):
            continue
            
        # Iterate through each destination station
        for dest in stations:
            if pd.isna(dest) or dest == origin:
                continue
                
            distance = row[dest]
            if pd.isna(distance):
                continue
                
            # Use sorted station names as key to ensure A->B and B->A use the same key
            stations_sorted = tuple(sorted([origin, dest]))
            key = f"{stations_sorted[0]}->{stations_sorted[1]}"
            distance_map[key] = float(distance)
    
    # Create output directory
    output_dir = Path('app/data')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save as JSON file
    with open(output_dir / 'distance_map.json', 'w', encoding='utf-8') as f:
        json.dump(distance_map, f, indent=2, ensure_ascii=False)
        
    print(f"Generated distance map with {len(distance_map)} entries")

if __name__ == '__main__':
    generate_distance_map() 