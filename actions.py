"""
This files contains your custom actions which can be used to run
custom Python code.

See this guide on how to implement these action:
https://rasa.com/docs/rasa/custom-actions


This is a simple example for a custom action which utters "Hello World!"

from typing import Any, Text, Dict, List

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher


class ActionChatGPT(Action):

    def name(self) -> Text:
        return "action_chatGPT"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:

        dispatcher.utter_message(text="Hello World!")

        return []
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet
import logging
import re


# 로거 설정
logging.basicConfig(level=logging.DEBUG)

# OrderManager 클래스로 현재 주문 목록을 저장
class OrderManager:
    def __init__(self):
        # 주문 관련 정보를 저장할 딕셔너리 초기화
        self.orders = {}  # 음료별 주문 수량을 저장하는 딕셔너리
        self.temperatures = {}  # 음료별 온도를 저장하는 딕셔너리
        self.sizes = {}  # 음료별 사이즈를 저장하는 딕셔너리
        self.additional_option = {}  # 음료별 추가 옵션을 저장하는 딕셔너리
        self.hot_drinks = ["허브티"]  # 항상 핫으로만 제공되는 음료 리스트
        self.ice_only_drinks = ["토마토주스", "키위주스", "망고스무디", "딸기스무디", "레몬에이드", "복숭아아이스티"]  # 항상 아이스로만 제공되는 음료 리스트

    def add_order(self, drink_type, quantity, temperature=None, size=None, additional_options=None):
        drink_type = standardize_drink_name(drink_type)  # 음료 이름 표준화
        
        # 새로운 음료 주문을 추가하거나 기존 주문에 수량을 추가하는 메서드
        if drink_type not in self.orders:
            # 음료 타입이 처음 주문될 경우 초기화
            self.orders[drink_type] = 0
            self.temperatures[drink_type] = []
            self.sizes[drink_type] = []
            self.additional_option[drink_type] = []

        # 음료 타입에 대한 주문 수량과 관련 정보를 업데이트
        self.orders[drink_type] += quantity
        self.temperatures[drink_type].extend([temperature] * quantity)
        self.sizes[drink_type].extend([size] * quantity)
        self.additional_option[drink_type].extend([additional_options] * quantity)

    def modify_order(self, old_drink_type, new_drink_type, quantity, temperature=None, size=None, additional_options=None):
        old_drink_type = standardize_drink_name(old_drink_type)  # 음료 이름 표준화
        new_drink_type = standardize_drink_name(new_drink_type)  # 음료 이름 표준화
        
        # 기존 주문을 새로운 주문으로 수정하는 메서드
        if old_drink_type in self.orders:
            # 기존 음료 주문을 제거
            self.subtract_order(old_drink_type, quantity, temperature, size, additional_options)
        # 새로운 음료 주문을 추가
        self.add_order(new_drink_type, quantity, temperature, size, additional_options)

    def subtract_order(self, drink_type, quantity, temperature=None, size=None, additional_options=None):
        drink_type = standardize_drink_name(drink_type)  # 음료 이름 표준화
        # 주문에서 특정 음료의 수량을 감소시키는 메서드
        if drink_type in self.orders:
            if quantity is None:
                quantity = 1
            indices_to_remove = []
            # 조건에 맞는 음료의 인덱스를 찾기
            for i in range(len(self.temperatures[drink_type])):
                if (self.temperatures[drink_type][i] == temperature) and (self.sizes[drink_type][i] == size) and (self.additional_option[drink_type][i] == additional_options):
                    indices_to_remove.append(i)
                    if len(indices_to_remove) == quantity:
                        break

            if len(indices_to_remove) < quantity:
                # 음료 수량이 부족할 경우 예외 발생
                raise ValueError(f"{drink_type}의 수량이 충분하지 않습니다.")
            else:
                # 음료 정보에서 해당 인덱스의 항목들을 제거
                for index in reversed(indices_to_remove):
                    del self.temperatures[drink_type][index]
                    del self.sizes[drink_type][index]
                    del self.additional_option[drink_type][index]
                self.orders[drink_type] -= quantity
                # 음료 수량이 0 이하일 경우 해당 음료 정보를 삭제
                if self.orders[drink_type] <= 0:
                    del self.orders[drink_type]
                    del self.temperatures[drink_type]
                    del self.sizes[drink_type]
                    del self.additional_option[drink_type]
        else:
            raise ValueError(f"{drink_type}은(는) 주문에 없습니다.")
        
    def modify_additional_options(self, drink_type, quantity, temperature, size, new_options, action):
        drink_type = standardize_drink_name(drink_type)  # 음료 이름 표준화
        logging.warning(f"추가옵션 추가 및 제거 실행")
        if drink_type in self.orders:
            indices_to_modify = []

            for i in range(len(self.additional_option[drink_type])):
                current_temp = self.temperatures[drink_type][i]
                current_size = self.sizes[drink_type][i]
                current_options = self.additional_option[drink_type][i].split(", ") if self.additional_option[drink_type][i] else []

                logging.warning(f"현재 옵션: {current_options}, 온도: {current_temp}, 사이즈: {current_size}")
                logging.warning(f"{temperature, current_temp, size}")
                if current_temp == temperature and current_size == size:
                    if action == "add":
                        if new_options:
                            new_options_list = new_options.split(", ")
                            logging.warning(f"새 옵션 리스트: {new_options_list}")
                            current_options.extend(new_options_list)
                        current_options = list(set(current_options))  # 중복 제거
                        logging.warning(f"중복 제거 후 옵션: {current_options}")
                    elif action == "remove":
                        remove_options_list = new_options.split(", ") if new_options else []
                        logging.warning(f"제거할 옵션 리스트: {remove_options_list}")

                        logging.warning(f"현재 옵션: {current_options}")

                        # remove_options_list에서 중복된 값을 찾아 제거
                        for option in set(remove_options_list):
                            logging.warning(f"옵션 제거 실행: {current_options}")
                            if remove_options_list.count(option) > 1:
                                current_options = [opt for opt in current_options if opt != option]
                        
                        logging.warning(f"제거 후 옵션: {current_options}")

                    self.additional_option[drink_type][i] = ", ".join(current_options)
                    indices_to_modify.append(i)
                    if len(indices_to_modify) == quantity:
                        break

            if len(indices_to_modify) < quantity:
                raise ValueError(f"{drink_type}의 추가 옵션 수량이 충분하지 않습니다.")
        else:
            raise ValueError(f"{drink_type}은(는) 주문에 없습니다.")

    def cancel_order(self):
        # 현재 모든 주문을 취소하고 초기화하는 메서드
        canceled_orders = self.orders.copy()  # 기존 주문을 백업
        self.orders = {}
        self.temperatures = {}
        self.sizes = {}
        self.additional_option = {}
        return canceled_orders  # 취소된 주문 반환

    def clear_order(self):
        # 현재 주문을 초기화하는 메서드
        self.orders.clear()
        self.temperatures.clear()
        self.sizes.clear()
        self.additional_option.clear()

    def get_orders(self):
        # 현재 주문 정보를 반환하는 메서드
        return self.orders

    def get_order_summary(self):
        # 현재 주문 요약 정보를 생성하여 반환하는 메서드
        summary = []
        for drink, quantity in self.orders.items():
            temperatures = self.temperatures.get(drink, [None] * quantity)
            sizes = self.sizes.get(drink, [None] * quantity)
            options = self.additional_option.get(drink, [None] * quantity)

            drink_summary = {}
            for i in range(quantity):
                temp = temperatures[i] if i < len(temperatures) else None
                size = sizes[i] if i < len(sizes) else None
                option = options[i] if i < len(options) else None
                key = (temp, size, option)
                if key in drink_summary:
                    drink_summary[key] += 1
                else:
                    drink_summary[key] = 1

            for (temp, size, option), count in drink_summary.items():
                summary_item = f"{drink}"
                if size:
                    summary_item = f"{summary_item} {size}"
                if temp:
                    summary_item = f"{temp} {summary_item}"
                if option:
                    # 여러 옵션을 "추가"라는 단어와 함께 출력
                    options_list = option.split(", ")
                    options_str = ", ".join(options_list) + " 추가"
                    summary_item = f"{summary_item} {options_str}"
                summary_item = f"{summary_item} {number_to_korean(count)} 잔"
                summary.append(summary_item.strip())
        return ", ".join(summary)
    
    def get_default_order_summary(self):
        # 기본 주문 요약 정보를 생성하여 반환하는 메서드
        summary = []
        for drink, quantity in self.orders.items():
            temperatures = self.temperatures.get(drink, ["핫"] * quantity)
            sizes = self.sizes.get(drink, ["미디움"] * quantity)
            options_list = self.additional_option.get(drink, ["없음"] * quantity)

            drink_summary = {}
            for i in range(quantity):
                # 항상 핫으로 제공되는 음료와 항상 아이스로 제공되는 음료 처리
                if drink in self.hot_drinks:
                    temp = "핫"
                elif drink in self.ice_only_drinks:
                    temp = "아이스"
                else:
                    temp = temperatures[i] if temperatures[i] else ("아이스" if drink in self.ice_only_drinks else "핫")
                size = sizes[i] if sizes[i] else "미디움"
                options = options_list[i] if options_list[i] else "없음"
                key = (temp, size, options)
                if key in drink_summary:
                    drink_summary[key] += 1
                else:
                    drink_summary[key] = 1

            for (temp, size, options), count in drink_summary.items():
                summary_item = f"{temp} {drink} {size}"
                if options != "없음":
                    summary_item = f"{summary_item} {options} 추가"
                summary_item = f"{summary_item} {number_to_korean(count)} 잔"
                summary.append(summary_item.strip())
        return ", ".join(summary)

order_manager = OrderManager()  # OrderManager 인스턴스 생성

# 엔티티 매핑
class OrderMapper:
    def __init__(self, entities, is_temperature_change=False, is_size_change=False):
        self.entities = sorted(entities, key=lambda x: x['start'])
        self.is_temperature_change = is_temperature_change  # 온도 변경 기능 실행 여부 플래그
        self.is_size_change = is_size_change  # 사이즈 변경 기능 실행 여부 플래그
        self.drinks = []
        self.suffixes = ("사이즈로", "사이즈", "으로", "으", "걸로", "로", "는", "은", "해주세요", "해서", "해", "한거", "이랑", "도")
        self._map_entities()

    # 주문 초기화
    def _initialize_order(self):
        return {
            "temperature": None,
            "drink_type": None,
            "size": None,
            "quantity": 1,
            "additional_options": []
        }

    # 엔티티 값에서 제거할 접미사 제거
    def clean_entity_values(self):
        for entity in self.entities:
            # drink_type 엔티티가 아닌 경우에만 접미사 제거
            if entity['entity'] != 'drink_type':
                value = entity["value"]
                for suffix in self.suffixes:
                    if value.endswith(suffix):
                        value = value[:-len(suffix)]
                        break
                entity["value"] = value

    def _map_entities(self):
        self.clean_entity_values()  # 엔티티 값 정리
        current_order = self._initialize_order()  # 현재 처리 중인 주문 초기화
        drink_type_count_temp = self._count_drink_types()  # 음료 타입 엔티티 개수 확인(온도용)
        drink_type_count_size = self._count_drink_types()  # 음료 타입 엔티티 개수 확인(사이즈용)

        temperature_entities_count = self._count_temperature_entities()  # 온도 엔티티 개수 확인
        apply_default_temperature = self.is_temperature_change and temperature_entities_count == 1
        size_entities_count = self._count_size_entities()  # 사이즈 엔티티 개수 확인
        apply_default_size = self.is_size_change and size_entities_count == 1

        # 모든 엔티티를 돌며 매핑
        for i, entity in enumerate(self.entities):
            if entity['entity'] == 'drink_type':
                if current_order['drink_type']:
                    self._complete_order(current_order)
                    current_order = self._initialize_order()

                if entity['value'] in ["아아", "아 아", "아", "아가"]:
                    current_order['temperature'] = "아이스"
                    current_order['drink_type'] = "아메리카노"
                elif entity['value'] in ["뜨아", "뜨 아", "뜨아아", "또", "응아", "쁘허", "뚜아","똬"]:
                    current_order['temperature'] = "핫"
                    current_order['drink_type'] = "아메리카노"
                else:
                    current_order['drink_type'] = standardize_drink_name(entity['value'])                
                    if apply_default_temperature:
                        current_order['temperature'] = "핫"
                    else:
                        temp_entity = self._find_previous_or_next_temperature_entity(i)
                        if temp_entity:
                            current_order['temperature'] = temp_entity
                        else:
                            current_order['temperature'] = "핫"

                if apply_default_size:
                    current_order['size'] = "미디움"
                else:
                    size_entity = self._find_next_or_previous_size_entity(i)
                    if size_entity:
                        current_order['size'] = size_entity
                    else:
                        current_order['size'] = "미디움"
                    
                drink_type_count_temp -= 1
                drink_type_count_size -= 1

            elif entity['entity'] == 'quantity':
                quantity = entity['value']
                quantity = standardize_quantity(quantity)  # 잔 수 표준화 적용
                current_order['quantity'] = int(quantity) if quantity.isdigit() else korean_to_number(quantity)

            elif entity['entity'] == 'size':
                current_order['size'] = standardize_size(entity['value'])

            elif entity['entity'] == 'additional_options':
                current_order['additional_options'].append(standardize_drink_name(standardize_option(entity['value'])))

        if current_order['drink_type']:
            self._complete_order(current_order)

    # 음료 타입 엔티티 개수 반환
    def _count_drink_types(self):
        return sum(1 for entity in self.entities if entity['entity'] == 'drink_type')

    # 사이즈 엔티티 개수 반환
    def _count_size_entities(self):
        return sum(1 for entity in self.entities if entity['entity'] == 'size')

    # 사이즈 매핑 알고리즘
    def _find_next_or_previous_size_entity(self, current_index):
        # 음료 종류 바로 뒤의 엔티티가 size인 경우
        if current_index + 1 < len(self.entities) and self.entities[current_index + 1]['entity'] == 'size':
            return standardize_size(self.entities[current_index + 1]['value'])
        
        # 온도 엔티티 바로 앞의 엔티티가 size인 경우
        if current_index > 0 and self.entities[current_index - 1]['entity'] == 'temperature':
            if current_index - 2 >= 0 and self.entities[current_index - 2]['entity'] == 'size':
                return standardize_size(self.entities[current_index - 2]['value'])
            
        # 온도 엔티티가 없는 경우 음료 종류 바로 앞의 엔티티가 size인 경우
        if current_index > 0 and self.entities[current_index - 1]['entity'] == 'size':
            return standardize_size(self.entities[current_index - 1]['value'])

        # 잔 수 엔티티 바로 뒤의 엔티티가 size인 경우
        for i in range(current_index + 1, len(self.entities)):
            if self.entities[i]['entity'] == 'size':
                return standardize_size(self.entities[i]['value'])
            if self.entities[i]['entity'] == 'drink_type':
                break
        return None

    # 온도 엔티티 개수 반환
    def _count_temperature_entities(self):
        return sum(1 for entity in self.entities if entity['entity'] == 'temperature')

    # 온도 매핑 알고리즘
    def _find_previous_or_next_temperature_entity(self, current_index):
        # drink_type의 바로 앞의 엔티티가 temperature인 경우
        if current_index > 0 and self.entities[current_index - 1]['entity'] == 'temperature':
            return self._map_temperature(self.entities[current_index - 1]['value'])
        
        # 뒤의 엔티티 중에서 temperature를 찾음
        for i in range(current_index + 1, len(self.entities)):
            if self.entities[i]['entity'] == 'temperature':
                if i + 1 < len(self.entities) and self.entities[i + 1]['entity'] == 'drink_type':
                    return None
                return self._map_temperature(self.entities[i]['value'])
        return None

    # 온도 값 일반화(아이스, 핫) 후 매핑
    def _map_temperature(self, value):
        return standardize_temperature(value)

    # 주문이 완성되지 않은 필드 기본값 설정 후 drinks 리스트에 추가
    def _complete_order(self, order):
        hot_drinks = ["허브티"]
        ice_only_drinks = ["토마토주스", "키위주스", "망고스무디", "딸기스무디", "레몬에이드", "복숭아아이스티"]

        if order['drink_type'] in hot_drinks:
            order['temperature'] = "핫"
        elif order['drink_type'] in ice_only_drinks:
            order['temperature'] = "아이스"
        else:
            if order['temperature'] is None:
                order['temperature'] = "핫"
        
        if order['size'] is None:
            order['size'] = "미디움"
        if order['quantity'] is None:
            order['quantity'] = 1

        self.drinks.append(order)

    # 완성된 음료 주문 데이터 반환
    def get_mapped_data(self):
        temperatures = [drink["temperature"] for drink in self.drinks]
        drink_types = [drink["drink_type"] for drink in self.drinks]
        sizes = [drink["size"] for drink in self.drinks]
        quantities = [drink["quantity"] for drink in self.drinks]
        additional_options = [", ".join(drink["additional_options"]) for drink in self.drinks]
        return temperatures, drink_types, sizes, quantities, additional_options

# 한국어 수량을 숫자로 변환하는 함수
def korean_to_number(korean: str) -> int:
    korean_number_map = {
        "한": 1,
        "두": 2,
        "세": 3,
        "네": 4,
        "다섯": 5,
        "여섯": 6,
        "일곱": 7,
        "여덟": 8,
        "아홉": 9,
        "열": 10
    }
    return korean_number_map.get(korean, 1)  # 기본값으로 1을 반환

# 숫자를 한국어 수량으로 변환하는 함수
def number_to_korean(number: int) -> str:
    korean_number_map = {
        1: "한",
        2: "두",
        3: "세",
        4: "네",
        5: "다섯",
        6: "여섯",
        7: "일곱",
        8: "여덟",
        9: "아홉",
        10: "열"
    }
    return korean_number_map.get(number, str(number))  # 기본값으로 숫자 문자열을 반환

# 음료 종류 및 띄어쓰기 표준화
def standardize_drink_name(name):
    # 음료 이름 변형을 표준 이름으로 매핑하는 사전
    drink_name_map = {
        "카페라테": "카페라떼",
        "카페라뗴": "카페라떼",
        "레모네이드" : "레몬에이드",
        "카라멜마키아또" : "카라멜마끼아또",
        "아보카도" : "아포카토",
        "키즈스" : "키위주스",
        "초콜릿" : "초콜릿라떼",
        "초콜릿대" : "초콜릿라떼",
        "바닐라떼" : "바닐라라떼",
        "카라멜막혔더" : "카라멜마끼아또",
        "복숭아ost" : "복숭아아이스티",
        "말자라때" : "말차라떼",
        "바닐라레떼" : "바닐라라떼",
        "아포가토" : "아포카토",
        "복숭아아이스크림" : "복숭아아이스티",
        "허벅지" : "허브티",
        "에스페로" : "에스프레소",
        "다기스무디" : "딸기스무디",
        "망고스머리" : "망고스무디",
        "토마토소스" : "토마토주스",
        "망고스뮤비" : "망고스무디",
        "쿠킹크림" : "쿠키앤크림",
        "쿠킹그림" : "쿠키앤크림",
        "쿠앤크" : "쿠키앤크림",
        "카페북한" : "카페모카",
        "tv스투스" : "키위주스",
        "Tv스투스" : "키위주스",
        "TV스투스" : "키위주스",
        "말잘할때" : "말차라떼",
        "허버트" : "허브티",
        "tv쥬스" : "키위주스",
        "Tv쥬스" : "키위주스",
        "TV쥬스" : "키위주스",
        "아프리카" : "아포카토",
        "마찰할때" : "말차라떼",
        "말찾았대" : "말차라떼",
        "라벨마끼아또" : "카라멜마끼아또",
        "카메라맡기어도" : "카라멜마끼아또",
        "복숭아st" : "복숭아아이스티",
        "복숭아St" : "복숭아아이스티",
        "복숭아ST" : "복숭아아이스티",
        "복숭아에스티" : "복숭아아이스티",
        "복숭아하이스틸" : "복숭아아이스티",
        "호텔" : "허브티",
        "말잘했다" : "말차라떼",
        "카라멜" : "카라멜마끼아또", 
        "라떼" : "카페라떼",
        "라뗴" : "카페라떼",
        "라때" : "카페라떼"
    }

    # 공백과 쉼표 제거
    standardized_name = re.sub(r'[\s,]+', '', name)

    # 매핑 사전을 사용하여 표준 이름으로 변환
    if standardized_name in drink_name_map:
        return drink_name_map[standardized_name]
    else:
        return standardized_name

# 온도를 표준화하는 함수
def standardize_temperature(value):
    if value in ["차갑게", "시원하게", "아이스", "차가운", "시원한"]:
        return "아이스"
    elif value in ["뜨겁게", "따뜻하게", "핫", "뜨거운", "따뜻한", "뜨뜻한", "하수", "hot"]:
        return "핫"
    return value

# 잔 수를 표준화하는 함수
def standardize_quantity(value):
    if value in ["한", "앉", "안", "환", "완", "라", "하나"]:
        return "한"
    elif value in ["두", "도"]:
        return "두"
    elif value in ["세", "재", "대"]:
        return "세"
    elif value in ["네", "내"]:
        return "네"
    elif value in ["다섯", "das"]:
        return "다섯"
    elif value in ["여섯"]:
        return "여섯"
    elif value in ["일곱"]:
        return "일곱"
    elif value in ["여덟"]:
        return "여덟"
    elif value in ["아홉"]:
        return "아홉"
    elif value in ["열"]:
        return "열"
    return value

# 사이즈를 표준화하는 함수
def standardize_size(value):
    if value in ["미디움", "보통", "중간", "기본", "톨", "비디오", "토"]:
        return "미디움"
    elif value in ["라지", "큰", "크게", "라의", "라디오"]:
        return "라지"
    elif value in ["엑스라지", "엑스라이즈", "제1 큰", "가장 큰", "제1 크게", "맥시멈"]:
        return "엑스라지"
    return value

# 추가옵션를 표준화하는 함수
def standardize_option(value):
    if value in ["샤츠", "셔츠", "사추", "샤타나", "4추가"]:
        return "샷"
    elif value in ["카라멜실업", "실룩실룩", "가라멜시럽", "카라멜시로"]:
        return "카라멜시럽"
    elif value in ["바닐라실업"]:
        return "바닐라시럽"
    elif value in ["비비크림"]:
        return "휘핑크림"
    return value

# 커피의 종류와 온도와 사이즈가 정해지지 않으면 오류 발생
def raise_missing_attribute_error(drinks):
    if not drinks:
        raise ValueError("정확한 음료의 종류를 말씀하여주세요.")
    for drink in drinks:
        if not drink["drink_type"]:
            raise ValueError("정확한 음료의 종류를 말씀하여주세요.")

# 주문
class ActionOrderConfirmation(Action):
    def name(self) -> Text:
        return "action_order_confirmation"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # # 현재 주문 정보 초기화(주문을 하는데 이전 주문 정보가 남아있으면 안됨)
            # order_manager.clear_order()
            # 최근 사용자 메시지에서 엔터티를 가져오기
            entities = [entity for entity in tracker.latest_message.get("entities", []) if entity.get("extractor") != "DIETClassifier"]
            user_text = tracker.latest_message.get("text", "")

            if "사이즈 업" in user_text:
                raise KeyError("size up")

            # 엔티티를 위치 순서로 정렬
            mapper = OrderMapper(entities)
            temperatures, drink_types, sizes, quantities, additional_options = mapper.get_mapped_data()

            logging.warning(f"주문 엔티티: {entities}")
            logging.warning(f"온도, 커피, 사이즈, 잔 수, 옵션: {temperatures} {drink_types} {sizes} {quantities} {additional_options}")

            # 고정된 온도 음료의 온도 확인
            hot_drinks = ["허브티"]
            ice_only_drinks = ["토마토주스", "키위주스", "망고스무디", "딸기스무디", "레몬에이드", "복숭아아이스티"]

            for i in range(len(drink_types)):
                if drink_types[i] in hot_drinks and temperatures[i] != "핫":
                    raise ValueError(f"{drink_types[i]}는(은) 온도를 변경하실 수 없습니다.")
                if drink_types[i] in ice_only_drinks and temperatures[i] != "아이스":
                    raise ValueError(f"{drink_types[i]}는(은) 온도를 변경하실 수 없습니다.")

            raise_missing_attribute_error(mapper.drinks)  # 음료 속성 검증

            if drink_types and quantities:
                for i in range(len(drink_types)):
                    order_manager.add_order(drink_types[i], quantities[i], temperatures[i], sizes[i], additional_options[i])

            confirmation_message = f"주문하신 음료는 {order_manager.get_order_summary()}입니다. 다른 추가 옵션이 필요하신가요?"
            dispatcher.utter_message(text=confirmation_message)

        except ValueError as e:
            dispatcher.utter_message(text=str(e))
        except Exception as e:
                dispatcher.utter_message(text=f"주문 접수 중 오류가 발생했습니다: {str(e)}")
        return []

# 주문 변경
class ActionModifyOrder(Action):
    def name(self) -> Text:
        return "action_modify_order"

    # 주어진 텍스트 범위 내에서 엔티티 추출
    def extract_entities(self, text, tracker):
        entities = []
        for entity in tracker.latest_message.get("entities", []):
            if entity.get("extractor") != "DIETClassifier" and entity["start"] >= text["start"] and entity["end"] <= text["end"]:
                entities.append(entity)
        return entities

    # 액션 실행 메소드
    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # 가장 최근 사용자 메시지에서 엔티티 추출
            modify_entities = [entity for entity in tracker.latest_message.get("entities", []) if entity.get("extractor") != "DIETClassifier"]
        
            mapper = OrderMapper(modify_entities)
            temperatures, drink_types, sizes, quantities, additional_options = mapper.get_mapped_data()
            user_text = tracker.latest_message.get("text", "")

            logging.warning(f"사용자 주문 변경 입력 내용: {modify_entities}")
            logging.warning(f"사용자 주문 변경 입력 내용: {user_text}")

            raise_missing_attribute_error(mapper.drinks)  # 음료 속성 검증

            # '대신' 또는 '말고'를 사용하여 주문 변경 여부 확인
            if "대신" in user_text or "말고" in user_text:
                # '대신' 또는 '말고'를 기준으로 텍스트 분리
                split_text = re.split("대신|말고", user_text)
                logging.warning(f"매칭 시도: {split_text}")
                if len(split_text) == 2:
                    target_part = {"text": split_text[0].strip(), "start": 0, "end": len(split_text[0].strip())}
                    new_part = {"text": split_text[1].strip(), "start": len(split_text[0]) + 2, "end": len(user_text)}

                    logging.warning(f"target_part 내용: {target_part}")
                    logging.warning(f"new_part 내용: {new_part}")

                    # 각각의 텍스트 부분에서 엔티티 추출
                    target_entities = self.extract_entities(target_part, tracker)
                    new_entities = self.extract_entities(new_part, tracker)

                    logging.warning(f"target_entities 내용: {target_entities}")
                    logging.warning(f"new_entities 내용: {new_entities}")

                    # 대상 및 새 엔티티를 매핑하여 데이터 추출
                    target_mapper = OrderMapper(target_entities)
                    target_temperatures, target_drink_types, target_sizes, target_quantities, target_additional_options = target_mapper.get_mapped_data()

                    new_mapper = OrderMapper(new_entities)
                    new_temperatures, new_drink_types, new_sizes, new_quantities, new_additional_options = new_mapper.get_mapped_data()

                    logging.warning(f"target_mapper 내용: {target_temperatures, target_drink_types, target_sizes, target_quantities, target_additional_options}")
                    logging.warning(f"new_mapper 내용: {new_temperatures, new_drink_types, new_sizes, new_quantities, new_additional_options}")

                    # 고정된 온도 음료의 온도 확인
                    hot_drinks = ["허브티"]
                    ice_only_drinks = ["토마토주스", "키위주스", "망고스무디", "딸기스무디", "레몬에이드", "복숭아아이스티"]

                    for i in range(len(new_drink_types)):
                        if new_drink_types[i] in hot_drinks and new_temperatures[i] != "핫":
                            raise ValueError(f"{new_drink_types[i]}는(은) 온도를 변경하실 수 없습니다.")
                        if new_drink_types[i] in ice_only_drinks and new_temperatures[i] != "아이스":
                            raise ValueError(f"{new_drink_types[i]}는(은) 온도를 변경하실 수 없습니다.")

                    # 기존 주문에서 대상 항목 제거
                    for i in range(len(target_drink_types)):
                        target_drink = target_drink_types[i]
                        target_quantity = target_quantities[i]
                        target_temperature = target_temperatures[i] if i < len(target_temperatures) else None
                        target_size = target_sizes[i] if i < len(target_sizes) else None
                        target_option = target_additional_options[i] if i < len(target_additional_options) else None
                        if target_drink in order_manager.get_orders():
                            order_manager.subtract_order(target_drink, target_quantity, target_temperature, target_size, target_option)
                        else:
                            dispatcher.utter_message(text=f"{target_drink}은(는) 주문에 없습니다.")
                            return []

                    # 새 항목을 기존 주문에 추가
                    for i in range(len(new_drink_types)):
                        new_drink = new_drink_types[i]
                        new_quantity = new_quantities[i]
                        new_size = new_sizes[i] if i < len(new_sizes) else None
                        new_temperature = new_temperatures[i] if i < len(new_temperatures) else None
                        new_option = new_additional_options[i] if i < len(new_additional_options) else None

                        if new_drink in order_manager.ice_only_drinks:
                            dispatcher.utter_message(text=f"{new_drink}는 아이스만 가능합니다.")
                            new_temperature = "아이스"
                        elif new_drink in order_manager.hot_drinks:
                            dispatcher.utter_message(text=f"{new_drink}는 핫만 가능합니다.")
                            new_temperature = "핫"

                        order_manager.add_order(new_drink, new_quantity, new_temperature, new_size, new_option)
            else:
                # '대신' 또는 '말고'가 없을 경우, 기존 주문을 비우고 새로 추가
                order_manager.clear_order()

                logging.warning(f"주문 변경 엔티티: {modify_entities}")

                for i in range(len(drink_types)):
                    new_drink = drink_types[i]
                    new_quantity = quantities[i]
                    new_size = sizes[i] if i < len(sizes) else None
                    new_temperature = temperatures[i] if i < len(temperatures) else None
                    new_option = additional_options[i] if i < len(additional_options) else None

                    if new_drink in order_manager.ice_only_drinks:
                        dispatcher.utter_message(text=f"{new_drink}는 아이스만 가능합니다.")
                        new_temperature = "아이스"
                    elif new_drink in order_manager.hot_drinks:
                        dispatcher.utter_message(text=f"{new_drink}는 핫만 가능합니다.")
                        new_temperature = "핫"

                    order_manager.add_order(new_drink, new_quantity, new_temperature, new_size, new_option)

            # 최종 주문 확인 메시지 생성 및 출력
            confirmation_message = f"주문이 수정되었습니다. 현재 주문은 {order_manager.get_order_summary()}입니다. 다른 추가 옵션이 필요하신가요?"
            dispatcher.utter_message(text=confirmation_message)
            return []
        except Exception as e:
            dispatcher.utter_message(text=f"주문 변경 중 오류가 발생했습니다: {str(e)}")
            return []

# 주문 제거
class ActionSubtractFromOrder(Action):
    def name(self) -> Text:
        # 액션의 이름을 반환하는 메소드
        return "action_subtract_from_order"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # 최근 사용자 메시지에서 DIETClassifier가 아닌 엔티티들을 가져옴
            subtract_entities = [entity for entity in tracker.latest_message.get("entities", []) if entity.get("extractor") != "DIETClassifier"]
            
            # OrderMapper를 사용하여 엔티티들을 매핑
            mapper = OrderMapper(subtract_entities)
            temperatures, drink_types, sizes, quantities, additional_options = mapper.get_mapped_data()

            logging.warning(f"사용자 주문 제거 입력 내용: {subtract_entities}")
            logging.warning(f"사용자 주문 제거 매핑 데이터: {temperatures, drink_types, sizes, quantities, additional_options}")

            raise_missing_attribute_error(mapper.drinks)  # 음료 속성 검증(아이스 들어간 음료 다 취소. 가 드링크 타입이 없는데 왜 에러가 안뜨지?)

            # 매핑된 데이터를 순회하면서 주문 제거
            for i in range(len(drink_types)):
                drink = drink_types[i]  # 음료 종류
                quantity = quantities[i]  # 잔 수
                size = sizes[i] if i < len(sizes) else None  # 사이즈
                temperature = temperatures[i] if i < len(temperatures) else None  # 온도
                additional_option = additional_options[i] if i < len(additional_options) else None  # 추가 옵션
                
                try:
                    # 주문에 해당 음료가 있는지 확인하고 제거
                    if drink in order_manager.get_orders():
                        logging.warning(f"{temperature, drink, size, quantity, additional_option}")
                        order_manager.subtract_order(drink, quantity, temperature, size, additional_option)
                    else:
                        raise ValueError(f"{drink}은(는) 등록되지 않은 커피입니다! 다시 주문해주세요.")
                except ValueError as e:
                    dispatcher.utter_message(text=str(e))

            # 남아있는 주문이 있는지 확인하고 사용자에게 메시지 전송
            if order_manager.get_orders():
                confirmation_message = f"주문에서 음료가 제거되었습니다. 현재 주문은 {order_manager.get_order_summary()}입니다. 다른 추가 옵션이 필요하신가요?"
                dispatcher.utter_message(text=confirmation_message)
            else:
                dispatcher.utter_message(text="모든 음료가 주문에서 제거되었습니다.")

            return []
        except ValueError as e:
            dispatcher.utter_message(text=str(e))
        except Exception as e:
            # 오류 발생 시 사용자에게 오류 메시지 전송
            dispatcher.utter_message(text=f"주문 제거 중 오류가 발생했습니다: {str(e)}")
            return []

# 주문 다중처리
class ActionAddSubtract(Action):
    def name(self) -> Text:
        return "action_add_subtract"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # 최근 사용자 메시지에서 엔티티 가져오기
            entities = sorted([entity for entity in tracker.latest_message.get("entities", []) if entity.get("extractor") != "DIETClassifier"], key=lambda x: x['start'])

            add_entities = []
            subtract_entities = []

            current_order = self._initialize_order()
            current_action = None

            for i, entity in enumerate(entities):
                if entity['entity'] == 'add' and (i == 0 or entities[i-1]['entity'] != 'additional_options'):
                    current_action = 'add'
                    if current_order['drink_type']:
                        add_entities.append(current_order)
                    current_order = self._initialize_order()
                elif entity['entity'] == 'subtract':
                    current_action = 'subtract'
                    if current_order['drink_type']:
                        subtract_entities.append(current_order)
                    current_order = self._initialize_order()
                else:
                    self._map_entity_to_order(entity, current_order)

            # 마지막 주문 처리
            if current_order['drink_type']:
                if current_action == 'add':
                    add_entities.append(current_order)
                elif current_action == 'subtract':
                    subtract_entities.append(current_order)

            # 매핑된 데이터 출력
            logging.warning(f"추가 엔티티: {add_entities}, 제거 엔티티: {subtract_entities}")

            # 추가 엔티티가 있는 경우 매핑 및 처리
            for order in add_entities:
                self._process_add(order)

            # 제거 엔티티가 있는 경우 매핑 및 처리
            for order in subtract_entities:
                self._process_subtract(order, dispatcher)

            # 정리된 최종 주문 리스트를 생성
            confirmation_message = f"주문이 수정되었습니다. 현재 주문은 {order_manager.get_order_summary()}입니다. 다른 추가 옵션이 필요하신가요?"
            dispatcher.utter_message(text=confirmation_message)
            return []
        except Exception as e:
            logging.exception("Exception occurred in action_add_subtract")
            dispatcher.utter_message(text="주문을 수정하는 중에 오류가 발생했습니다. 다시 시도해주세요.")
            return []

    def _initialize_order(self):
        return {
            "temperature": "핫",
            "drink_type": None,
            "size": "미디움",
            "quantity": 1,
            "additional_options": []
        }

    def _map_entity_to_order(self, entity, order):
        if entity['entity'] == 'drink_type':
            order['drink_type'] = standardize_drink_name(entity['value'])
        elif entity['entity'] == 'quantity':
            quantity = entity['value']
            order['quantity'] = int(quantity) if quantity.isdigit() else korean_to_number(quantity)
        elif entity['entity'] == 'temperature':
            order['temperature'] = standardize_temperature(entity['value'])
        elif entity['entity'] == 'size':
            order['size'] = standardize_size(entity['value'])
        elif entity['entity'] == 'additional_options':
            order['additional_options'].append(standardize_option(entity['value']))

    def _process_subtract(self, order, dispatcher):
        try:
            if order['drink_type'] in order_manager.get_orders():
                order_manager.subtract_order(order['drink_type'], order['quantity'], order['temperature'], order['size'], ", ".join(order['additional_options']))
            else:
                raise ValueError(f"{order['drink_type']}은(는) 등록되지 않은 커피입니다! 다시 주문해주세요.")
        except ValueError as e:
            dispatcher.utter_message(text=str(e))

    def _process_add(self, order):
        # 고정된 온도 음료의 온도 확인
        hot_drinks = ["허브티"]
        ice_only_drinks = ["토마토주스", "키위주스", "망고스무디", "딸기스무디", "레몬에이드", "복숭아아이스티"]

        if order['drink_type'] in hot_drinks and order['temperature'] != "핫":
            raise ValueError(f"{order['drink_type']}는(은) 온도를 변경하실 수 없습니다.")
        if order['drink_type'] in ice_only_drinks and order['temperature'] != "아이스":
            raise ValueError(f"{order['drink_type']}는(은) 온도를 변경하실 수 없습니다.")

        order_manager.add_order(order['drink_type'], order['quantity'], order['temperature'], order['size'], ", ".join(order['additional_options']))
        
# 주문 확인
class ActionOrderFinish(Action):
    def name(self) -> Text:
        return "action_order_finish"

    # 주문을 완료하는 액션 실행
    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # 주문 데이터 확인
            if not order_manager.get_orders():
                # 주문이 없는 경우
                dispatcher.utter_message(text="장바구니에 주문이 없습니다. 다시 주문해 주세요.")
                return []
            
            # 최종 주문 메시지 생성
            final_message = f"주문이 완료되었습니다. 주문하신 음료는 {order_manager.get_default_order_summary()}입니다. 결제는 하단의 카드리더기로 결제해 주시기 바랍니다. 감사합니다."
            dispatcher.utter_message(text=final_message)

            # 주문 완료 후 저장된 커피 데이터 초기화
            order_manager.clear_order()

            return []
        except Exception as e:
            # 오류 발생 시 예외 처리
            logging.exception("Exception occurred in action_order_finish")
            dispatcher.utter_message(text="결제 중 오류가 발생했습니다. 다시 시도해주세요.")
            return []

# 주문 취소
class ActionCancelOrder(Action):
    def name(self) -> Text:
        return "action_cancel_order"

    # 주문을 취소하는 액션 실행
    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # 현재 주문된 음료 목록 가져오기
            current_orders = order_manager.get_orders()

            if not current_orders:
                # 취소할 주문이 없는 경우
                dispatcher.utter_message(text="취소할 주문이 없습니다.")
                return []

            # 주문 취소 메시지 생성
            cancellation_message = f"모든 주문이 취소되었습니다. 취소된 음료는 {order_manager.get_default_order_summary()}입니다. 새로운 주문을 원하시면 말씀해주세요."
            order_manager.clear_order()
            
            dispatcher.utter_message(text=cancellation_message)
            return []
        except Exception as e:
            # 오류 발생 시 예외 처리
            logging.exception("Exception occurred in action_cancel_order")
            dispatcher.utter_message(text="주문을 취소하는 중에 오류가 발생했습니다. 다시 시도해주세요.")
            return []

# 커피 추천
class ActionCoffeeRecommendation(Action):
    def name(self) -> Text:
        return "action_coffee_recommendation"

    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        # 최근 사용자 메시지에서 텍스트 가져오기, 만약 질문에 따라 나오는 커피의 종류가 바뀌게 하고싶다면 텍스트를 가져와서 re.search로 키워드를 판단해서 elif 다양한 경우 출력 가능
        # user_text = tracker.latest_message.get("text", "")

        # 사용자의 질문에 따라 다른 커피를 추천할 수 있도록 switch 문 대신 if-elif-else 문을 사용 -> 음료수나 뭐 다른 것도 추천한다면 내용을 바꿔야함
        # if re.search(r"인기", user_text):
        #     recommended_coffees = ["아메리카노", "카페라떼", "카푸치노"]
        #     recommedded_text = "저희 매장에서 가장 인기가 많은 커피로는 "
        # elif re.search(r"시그니처", user_text):
        #     recommended_coffees = ["아메리카노", "카푸치노", "에스프레소"]
        #     recommedded_text = "저희 매장의 시그니처 커피로는 "
        # elif re.search(r"시즌", user_text):
        #     recommended_coffees = ["아메리카노", "카페라떼", "에스프레소"]
        #     recommedded_text = "저희 매장 시즌 커피로는 "
        # else:
        #     recommended_coffees = ["아메리카노", "카페라떼", "카푸치노", "에스프레소"]
        #     recommedded_text = "저희 매장이 추천하는 커피로는 "

        recommended_coffees = ["아메리카노", "카페라떼", "카푸치노", "에스프레소"]
        recommended_coffees_str = ", ".join(recommended_coffees)
        recommedded_message = f"저희 매장이 추천하는 커피로는 {recommended_coffees_str} 등이 있습니다. 어떤 커피을 원하시나요?"
        # recommedded_message = f"{recommedded_text} {recommended_coffees_str} 등이 있습니다. 어떤 것을 원하시나요?"
        dispatcher.utter_message(text=recommedded_message)

        return []

# 커피 사이즈 변경
class ActionSelectCoffeeSize(Action):
    def name(self) -> Text:
        return "action_select_coffee_size"  # 액션의 이름을 정의하는 메서드

    # start 값이 가장 큰, 즉 사용자의 대화에서 가장 마지막에 오는 size 엔티티 값을 추출
    def extract_last_size(self, entities):
        # size 엔티티를 필터링하여 해당 엔티티들만 리스트로 만듦
        size_entities = [entity for entity in entities if entity["entity"] == "size"]
        # 필터링된 size 엔티티가 있을 경우
        if size_entities:
            # 'start' 값을 기준으로 가장 큰 엔티티를 찾고, 해당 엔티티의 'value' 값을 반환
            return max(size_entities, key=lambda x: x['start'])["value"]
        return None  # size 엔티티가 없을 경우 None 반환

    # 커피 사이즈를 변경하는 액션 실행
    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # 최근 사용자 메시지에서 엔터티를 가져오기
            entities = [entity for entity in tracker.latest_message.get("entities", []) if entity.get("extractor") != "DIETClassifier"]
            user_text = tracker.latest_message.get("text", "")

            if "사이즈 업" in user_text:
                raise KeyError("size up")

            # 엔티티를 위치 순서로 정렬하고 매핑
            mapper = OrderMapper(entities, is_size_change=True)
            temperatures, drink_types, sizes, quantities, additional_options = mapper.get_mapped_data()

            # 로그로 입력된 엔티티와 매핑된 데이터를 출력
            logging.warning(f"커피 사이즈 변경 입력 내용 텍스트: {user_text}")
            logging.warning(f"커피 사이즈 변경 입력 내용 엔티티: {entities}")
            logging.warning(f"커피 사이즈 변경 매핑 데이터: {temperatures, drink_types, sizes, quantities, additional_options}")

            raise_missing_attribute_error(mapper.drinks)  # 음료 속성 검증

            # 가장 마지막에 오는 size 엔티티 값을 new_size로 설정
            new_size = self.extract_last_size(entities)

            if new_size is None:
                dispatcher.utter_message(text="새로운 사이즈를 지정해주세요.")
                return []  # 새로운 사이즈가 지정되지 않으면 메서드를 종료

            # 현재 사이즈를 구분
            current_sizes = [entity["value"] for entity in entities if entity["entity"] == "size" and entity["value"] != new_size]
            current_size = current_sizes[-1] if current_sizes else "미디움"

            for i in range(len(drink_types)):
                drink = drink_types[i]  # 변경할 음료의 종류
                quantity = quantities[i] if quantities[i] is not None else 1  # 변경할 음료의 수량
                temperature = temperatures[i] if i < len(temperatures) else None  # 음료의 온도
                additional_option = additional_options[i] if i < len(additional_options) else None  # 추가 옵션

                # 로그로 변경할 음료의 정보 출력
                logging.warning(f"온도: {temperature}, 변경 대상 음료: {drink}, 수량: {quantity}, 현재 사이즈: {current_size}, 새로운 사이즈: {new_size}")

                try:
                    # 현재 주문된 음료를 기존 사이즈로 제거
                    order_manager.subtract_order(drink, quantity, temperature, current_size, additional_option)
                    # 새로운 사이즈로 주문 추가
                    order_manager.add_order(drink, quantity, temperature, new_size, additional_option)
                except ValueError as e:
                    # 오류 발생 시 사용자에게 메시지 전달
                    dispatcher.utter_message(text=str(e))
                    return []

            # 사이즈 변경 완료 메시지 생성 및 사용자에게 전달
            confirmation_message = f"사이즈가 변경되었습니다. 주문하신 음료는 {order_manager.get_order_summary()}입니다. 다른 추가 옵션이 필요하신가요?"
            dispatcher.utter_message(text=confirmation_message)

            return []
        
        except Exception as e:
            # 예외 발생 시 사용자에게 메시지 전달
            dispatcher.utter_message(text=f"사이즈 변경 중 오류가 발생했습니다: {str(e)}")
            return []

# 커피 온도 선택
class ActionSelectCoffeeTemperature(Action):
    def name(self) -> Text:
        return "action_select_coffee_temperature"  # 액션의 이름을 정의하는 메서드

    # 가장 마지막에 오는 temperature 엔티티 값을 추출하고 변환
    def extract_last_temperature(self, entities):
        temperature_entities = [entity for entity in entities if entity["entity"] == "temperature"]
        if temperature_entities:
            last_temp = max(temperature_entities, key=lambda x: x['start'])["value"]
            # '차갑게', '시원하게', '뜨겁게', '따뜻하게'를 각각 '아이스'와 '핫'으로 변환
            if last_temp in ["차갑게", "시원하게", "차가운", "시원한"]:
                return "아이스"
            elif last_temp in ["뜨겁게", "따뜻하게", "뜨거운", "따뜻한", "뜨뜻한", "따듯한"]:
                return "핫"
            return last_temp
        return None  # temperature 엔티티가 없을 경우 None 반환

    # 커피 온도를 변경하는 액션 실행
    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # 최근 사용자 메시지에서 엔터티를 가져오기
            entities = [entity for entity in tracker.latest_message.get("entities", []) if entity.get("extractor") != "DIETClassifier"]
            
            # 엔티티를 위치 순서로 정렬하고 매핑
            mapper = OrderMapper(entities, is_temperature_change=True)
            temperatures, drink_types, sizes, quantities, additional_options = mapper.get_mapped_data()

            # 로그로 입력된 엔티티와 매핑된 데이터를 출력
            logging.warning(f"커피 온도 변경 입력 내용: {entities}")
            logging.warning(f"커피 온도 변경 매핑 데이터: {temperatures, drink_types, sizes, quantities, additional_options}")

            # 고정된 온도 음료의 온도 확인
            hot_drinks = ["허브티"]
            ice_only_drinks = ["토마토주스", "키위주스", "망고스무디", "딸기스무디", "레몬에이드", "복숭아아이스티"]

            for i in range(len(drink_types)):
                if drink_types[i] in hot_drinks and temperatures[i] != "핫":
                    raise ValueError(f"{drink_types[i]}는(은) 온도를 변경하실 수 없습니다.")
                if drink_types[i] in ice_only_drinks and temperatures[i] != "아이스":
                    raise ValueError(f"{drink_types[i]}는(은) 온도를 변경하실 수 없습니다.")

            raise_missing_attribute_error(mapper.drinks)  # 음료 속성 검증

            # 가장 마지막에 오는 temperature 엔티티 값을 new_temperature로 설정
            new_temperature = self.extract_last_temperature(entities)

            if new_temperature is None:
                dispatcher.utter_message(text="새로운 온도를 지정해주세요.")
                return []  # 새로운 온도가 지정되지 않으면 메서드를 종료

            for i in range(len(drink_types)):
                drink = drink_types[i]  # 변경할 음료의 종류
                quantity = quantities[i] if quantities[i] is not None else 1  # 변경할 음료의 수량
                size = sizes[i] if i < len(sizes) else "미디움"  # 음료의 사이즈
                additional_option = additional_options[i] if i < len(additional_options) else None  # 추가 옵션

                # 기존 주문에서 현재 온도를 가져옴
                current_temperature = temperatures[i] if i < len(temperatures) else None

                # 로그로 변경할 음료의 정보 출력
                logging.warning(f"변경 대상 음료: {drink}, 수량: {quantity}, 현재 온도: {current_temperature}, 새로운 온도: {new_temperature}, 사이즈: {size}, 추가 옵션: {additional_option}")

                try:
                    # 현재 주문된 음료를 기존 온도로 제거
                    order_manager.subtract_order(drink, quantity, current_temperature, size, additional_option)
                    # 새로운 온도로 주문 추가
                    order_manager.add_order(drink, quantity, new_temperature, size, additional_option)
                except ValueError as e:
                    # 오류 발생 시 사용자에게 메시지 전달
                    dispatcher.utter_message(text=str(e))
                    return []

            # 온도 변경 완료 메시지 생성 및 사용자에게 전달
            confirmation_message = f"온도를 변경하셨습니다. 주문하신 음료는 {order_manager.get_order_summary()}입니다. 다른 추가 옵션이 필요하신가요?"
            dispatcher.utter_message(text=confirmation_message)

            return []
        except Exception as e:
            # 예외 발생 시 사용자에게 메시지 전달
            dispatcher.utter_message(text=f"커피 온도 변경 중 오류가 발생했습니다: {str(e)}")
            return []

# 커피 추가 옵션 추가 및 제거
class ActionAddAdditionalOptions(Action):
    # 액션의 이름을 정의
    def name(self) -> Text:
        return "action_addsub_additional_options"
    
    # 커피 추가 옵션을 변경하는 액션 실행
    async def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
    ) -> List[Dict[Text, Any]]:
        try:
            # 최신 사용자 메시지에서 DIETClassifier가 아닌 엔티티를 가져오기
            entities = [entity for entity in tracker.latest_message.get("entities", []) if entity.get("extractor") != "DIETClassifier"]
            
            # 엔티티를 정렬하고 매핑
            mapper = OrderMapper(entities)
            temperatures, drink_types, sizes, quantities, additional_options = mapper.get_mapped_data()

            # 디버깅을 위한 로그 출력
            logging.warning(f"추가 옵션 변경 입력 내용: {entities}")
            logging.warning(f"추가 옵션 변경 매핑 데이터: {temperatures, drink_types, sizes, quantities, additional_options}")

            raise_missing_attribute_error(mapper.drinks)  # 음료 속성 검증

            # 추가할 새로운 옵션이 없으면 사용자에게 메시지 출력하고 종료
            if not additional_options:
                dispatcher.utter_message(text="추가할 새로운 옵션을 지정해주세요.")
                return []

            # 매핑된 데이터를 사용하여 주문 정보 업데이트
            for i in range(len(drink_types)):
                drink = drink_types[i]  # 음료 종류
                quantity = quantities[i] if quantities[i] is not None else 1  # 잔 수
                temperature = temperatures[i] if i < len(temperatures) else "핫"  # 온도
                size = sizes[i] if i < len(sizes) else "미디움"  # 사이즈
                current_additional_option = additional_options[i] if i < len(additional_options) else None  # 현재 추가 옵션

                logging.warning(f"현재 추가 옵션: {current_additional_option}")
                
                # 추가옵션을 제거하는건지 추가하는건지 확인
                if "빼" in tracker.latest_message.get("text", ""):
                    action = "remove"
                else:
                    action = "add"

                logging.warning(f"order_manager 실행 직전: {drink, quantity, temperature, size, current_additional_option, action}")
                order_manager.modify_additional_options(drink, quantity, temperature, size, current_additional_option, action)

            # 최종 확인 메시지 생성 및 사용자에게 전달
            confirmation_message = f"말씀하신 옵션이 변경 되었습니다. 주문하신 음료는 {order_manager.get_order_summary()}입니다. 다른 추가 옵션이 필요하신가요?"
            dispatcher.utter_message(text=confirmation_message)

            return []
        except Exception as e:
            # 예외 발생 시 사용자에게 메시지 전달
            dispatcher.utter_message(f"말씀하신 {drink}는 주문 되어있지 않습니다. 새로운 주문을 요청 해주시거나, 해당 주문의 내용을 정확하게 말씀하여 주세요.")
            return []
        


# # 주문 추가
# class ActionAddToOrder(Action):
#     def name(self) -> Text:
#         # 액션의 이름을 반환하는 메소드
#         return "action_add_to_order"

#     async def run(
#         self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: Dict[Text, Any]
#     ) -> List[Dict[Text, Any]]:
#         try:
#             # 최근 사용자 메시지에서 DIETClassifier가 아닌 엔티티들을 가져옴
#             add_entities = [entity for entity in tracker.latest_message.get("entities", []) if entity.get("extractor") != "DIETClassifier"]
            
#             # OrderMapper를 사용하여 엔티티들을 매핑
#             mapper = OrderMapper(add_entities)
#             temperatures, drink_types, sizes, quantities, additional_options = mapper.get_mapped_data()

#             logging.warning(f"사용자 주문 추가 입력 내용: {add_entities}")
#             logging.warning(f"주문 추가 온도, 커피, 사이즈, 잔 수, 옵션: {temperatures} {drink_types} {sizes} {quantities} {additional_options}")

#             raise_missing_attribute_error(mapper.drinks)  # 음료 속성 검증

#             # 매핑된 데이터를 순회하면서 주문 추가
#             for i in range(len(drink_types)):
#                 drink = drink_types[i]  # 음료 종류
#                 quantity = quantities[i]  # 잔 수
#                 size = sizes[i] if i < len(sizes) else None  # 사이즈
#                 temperature = temperatures[i] if i < len(temperatures) else None  # 온도
#                 additional_option = additional_options[i] if i < len(additional_options) else None  # 추가 옵션
                
#                 # 음료의 온도가 아이스나 핫으로 강제되는지 확인
#                 if drink in order_manager.ice_only_drinks and temperature != "아이스":
#                     dispatcher.utter_message(text=f"{drink}는 아이스만 있습니다. 다시 주문해주세요.")
#                     return []
#                 elif drink in order_manager.hot_drinks and temperature != "핫":
#                     dispatcher.utter_message(text=f"{drink}는 핫만 있습니다. 다시 주문해주세요")
#                     return []

#                 # 주문에 음료 추가
#                 order_manager.add_order(drink, quantity, temperature, size, additional_option)

#             # 최종 주문 확인 메시지 생성 및 출력
#             confirmation_message = f"주문하신 음료는 {order_manager.get_order_summary()}입니다. 다른 추가 옵션이 필요하신가요?"
#             dispatcher.utter_message(text=confirmation_message)
#             dispatcher.utter_message(response="utter_ask_question")
#             return []
#         except Exception as e:
#             dispatcher.utter_message(text=f"주문 접수 중 오류가 발생했습니다: {str(e)}")