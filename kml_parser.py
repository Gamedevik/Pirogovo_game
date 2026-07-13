import xml.etree.ElementTree as ET
import re

def parse_kml(kml_file):
    """Парсит KML и возвращает список территорий"""
    
    tree = ET.parse(kml_file)
    root = tree.getroot()
    
    # Пространство имён
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    territories = []
    
    # Ищем все Placemark с полигонами
    for placemark in root.findall('.//kml:Placemark', ns):
        name = placemark.find('kml:name', ns)
        name_text = name.text if name is not None else "Без названия"
        
        # Описание (название фракции)
        description = placemark.find('kml:description', ns)
        faction_name = description.text if description is not None else name_text
        
        # Ищем полигон
        polygon = placemark.find('.//kml:Polygon', ns)
        if polygon is not None:
            # Координаты
            coords_elem = polygon.find('.//kml:coordinates', ns)
            if coords_elem is not None:
                coords_text = coords_elem.text.strip()
                points = []
                for coord in coords_text.split():
                    parts = coord.split(',')
                    if len(parts) >= 2:
                        lon = float(parts[0])
                        lat = float(parts[1])
                        points.append({'lat': lat, 'lon': lon})
                
                # Ищем стиль (цвет)
                style_url = placemark.find('kml:styleUrl', ns)
                style_id = style_url.text.replace('#', '') if style_url is not None else None
                
                territories.append({
                    'name': name_text,
                    'faction': faction_name,
                    'points': points,
                    'style_id': style_id,
                    'center': get_center(points) if points else None
                })
    
    return territories

def get_center(points):
    """Вычисляет центр полигона"""
    if not points:
        return None
    lat = sum(p['lat'] for p in points) / len(points)
    lon = sum(p['lon'] for p in points) / len(points)
    return {'lat': lat, 'lon': lon}

if __name__ == "__main__":
    territories = parse_kml('Карта развалившегося пирогово_01-07-2025_18-11-29.kml')
    for t in territories:
        print(f"📍 {t['faction']} -> {len(t['points'])} точек")