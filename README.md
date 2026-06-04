# WMS (Warehouse Management System) — aplikacja konsolowa w Pythonie

Autor: Robert Dzienio  

Prosty system magazynowy (WMS) napisany w Pythonie w oparciu o programowanie obiektowe. 

---

## Funkcjonalności

System umożliwia:

### Zarządzanie produktami
- dodawanie produktów
- edycja danych (nazwa, ilość, cena)
- usuwanie produktów
- przegląd listy produktów

### Lokalizacje magazynowe
- tworzenie lokalizacji (strefa, regał, półka)
- przegląd lokalizacji
- kontrola pojemności i zajętości

### Przyjęcia towaru (PZ)
- zwiększenie stanu magazynowego
- przypisanie towaru do lokalizacji
- walidacja dostępnego miejsca

### Wydania towaru (WZ)
- zmniejszenie stanu magazynowego
- kontrola dostępności towaru w lokalizacji

### Raporty i statystyki
- stan magazynu posortowany wg wartości
- produkty o niskim stanie (≤ 5 szt.)
- lista pustych lokalizacji
- łączna wartość magazynu
- historia dokumentów PZ/WZ

### Role użytkowników
- **Worker (operator magazynu)**:
  - operacje PZ/WZ
  - przegląd produktów i lokalizacji
- **Manager (kierownik)**:
  - pełne zarządzanie systemem
  - dostęp do raportów

---

## Zastosowane mechanizmy

Projekt pokazuje praktyczne użycie elementów omawianych na zajęciach.

### Programowanie obiektowe (OOP)
- klasy i obiekty
- hermetyzacja (`_store`, `_users`)
- dziedziczenie (`User`, `Worker`, `Manager`)
- polimorfizm (`menu()` dla różnych ról)
- abstrakcja (`ABC`, `abstractmethod`)

### `@dataclass`
Wykorzystane do modelowania danych:
- `Product`
- `Location`
- `WarehouseDocument`
- `DocumentLine`

brak boilerplate’u (`__init__`, `__repr__`)

---

### Pydantic — walidacja danych
Modele wejściowe:
- `ProductInput`
- `LocationInput`
- `DocumentInput`

Zastosowanie:
- walidacja typów
- ograniczenia (`Field`)
- walidatory (`field_validator`, `model_validator`)

---