import json

def get_region_name(lat, lon):
    if lon < 107.57550029969997 and lat < -6.854801002313785:
        return "Ciwaruga"
    if lat > -6.867635007095059 and lon > 107.57550029969997:
        return "Gerlong"
    if -6.873184306079369 <= lat <= -6.867635007095059 and lon > 107.57550029969997:
        return "Sarijadi"
    if -6.8750593479462285 <= lat < -6.873184306079369 and lon > 107.57550029969997:
        return "Sariasih"
    if lat < -6.8750593479462285 and lon > 107.57550029969997:
        return "Sarimanah"
    return "Unknown"

def process_feature(feature):
    lat = feature['properties']['y']
    lon = feature['properties']['x']
    feature['properties']['region_name'] = get_region_name(lat, lon)
    for key in ['street_count', 'ref', 'highway']:
        feature['properties'].pop(key, None)
    return feature

def convert_file(input_file, output_file):
    with open(input_file, 'r') as f:
        data = json.load(f)
    
    # Asumsi data berupa FeatureCollection
    if 'features' in data:
        for i, feature in enumerate(data['features']):
            data['features'][i] = process_feature(feature)
    else:
        # Jika cuma 1 feature
        data = process_feature(data)
    
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=4)
    print(f"File berhasil dikonversi dan disimpan di {output_file}")

# Contoh pemanggilan
convert_file('logic/graph/intersections_named_final.geojson', 'output.geojson')
