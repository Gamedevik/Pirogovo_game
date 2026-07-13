import xml.etree.ElementTree as ET
import re

def parse_kml(kml_file_path):
    """Парсит KML-файл и возвращает список территорий"""
    
    tree = ET.parse(kml_file_path)
    root = tree.getroot()
    
    ns = {'kml': 'http://www.opengis.net/kml/2.2'}
    
    territories = []
    
    # Цвета для фракций (из KML)
    color_map = {
        'Территории подконтрольные сенату': '#4345ed',
        'Моряки пирогово(Пираты сыпычевского пруда)': '#c97b17',
        'Гвардия Князя': '#ff1eb5',
        'Территоря разбойников': '#595959',
        'Рабочие Пироговской ГЭС': '#79470e',
        'Вольные железнодорожники(Анархисты)': '#0e3d79',
        'Территория, подчиняющиеся Асгарычу Шигапову': '#1ed2ff',
        'Территория преступных синдикатов': '#03ad1b',
        'Территория негров(Эту землю им лично дал князь)': '#4345ed',
        'Военный округ, созданный для борьбы с разбойниками': '#03ad1b',
        'Правительство мотоциклистов': '#4345ed',
        'Независимые ВВС Пирогово': '#1ed2ff',
        'Территория Рабочих и крестьян Пирогово': '#595959',
        'Территоря баронов(там куча независымых государств обьединенныз в один альянс)': '#00a197',
        'Империя пятерочки': '#4345ed',
        'Территория Новых свободных студентов сам гупса': '#79470e',
        'Союз Шундов и Татарбазара': '#03ad1b'
    }
    
    for placemark in root.findall('.//kml:Placemark', ns):
        name = placemark.find('kml:name', ns)
        name_text = name.text if name is not None else "Без названия"
        
        description = placemark.find('kml:description', ns)
        faction_name = description.text if description is not None else name_text
        
        # Очищаем название фракции от лишнего
        faction_name = faction_name.strip()
        if 'CDATA' in faction_name:
            faction_name = re.sub(r'<.*?>', '', faction_name)
            faction_name = faction_name.strip()
        
        polygon = placemark.find('.//kml:Polygon', ns)
        if polygon is not None:
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
                
                if points:
                    # Вычисляем центр
                    center_lat = sum(p['lat'] for p in points) / len(points)
                    center_lon = sum(p['lon'] for p in points) / len(points)
                    
                    territories.append({
                        'name': name_text,
                        'faction': faction_name,
                        'points': points,
                        'center': {'lat': center_lat, 'lon': center_lon},
                        'color': color_map.get(faction_name, '#666666'),
                        'population': 100 + len(points) * 10,
                        'resources': {
                            'wood': 50 + len(points) * 5,
                            'food': 50 + len(points) * 5,
                            'gold': 20 + len(points) * 2
                        }
                    })
    
    return territories

if __name__ == "__main__":
    import json
    territories = parse_kml('data/Карта развалившегося пирогово_01-07-2025_18-11-29.kml')
    print(f"✅ Загружено {len(territories)} территорий")
    for t in territories[:5]:
        print(f"  - {t['faction']} ({len(t['points'])} точек)")