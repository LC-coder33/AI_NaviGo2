import googlemaps
from pprint import pprint
import json
from typing import Dict, List, Optional
from config import GOOGLE_CLOUD_API_KEY

class PlaceTypeChecker:
    def __init__(self, api_key: str = GOOGLE_CLOUD_API_KEY):
        self.gmaps = googlemaps.Client(key=api_key)
    
    def search_place(self, query: str) -> List[Dict]:
        """장소 검색 결과 반환"""
        try:
            result = self.gmaps.places(query=query)
            return result.get('results', [])
        except Exception as e:
            print(f"검색 중 에러 발생: {e}")
            return []
    
    def get_place_details(self, place_id: str) -> Optional[Dict]:
        """장소 상세 정보 반환"""
        try:
            return self.gmaps.place(place_id)
        except Exception as e:
            print(f"상세 정보 조회 중 에러 발생: {e}")
            return None
    
    def check_place_types(self, query: str):
        """장소 검색 후 타입 정보 출력"""
        # 장소 검색
        results = self.search_place(query)
        if not results:
            print(f"'{query}'에 대한 검색 결과가 없습니다.")
            return
        
        # 첫 번째 결과의 상세 정보 조회
        first_result = results[0]
        place_id = first_result['place_id']
        details = self.get_place_details(place_id)
        
        if not details:
            print(f"'{query}'의 상세 정보를 가져올 수 없습니다.")
            return
        
        # 결과 출력
        place_result = details['result']
        print("\n=== 장소 정보 ===")
        print(f"이름: {place_result.get('name', 'N/A')}")
        print(f"주소: {place_result.get('formatted_address', 'N/A')}")
        print(f"평점: {place_result.get('rating', 'N/A')}")
        print(f"리뷰 수: {place_result.get('user_ratings_total', 'N/A')}")
        print("\n=== Place Types ===")
        pprint(place_result.get('types', []))
        
        # JSON 파일로 저장
        filename = f"{query.replace(' ', '_')}_place_info.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(place_result, f, ensure_ascii=False, indent=2)
        print(f"\n상세 정보가 {filename}에 저장되었습니다.")

def main():
    checker = PlaceTypeChecker()
    
    while True:
        query = input("\n검색할 장소를 입력하세요 (종료하려면 'q' 입력): ")
        if query.lower() == 'q':
            break
        
        checker.check_place_types(query)

if __name__ == "__main__":
    main()