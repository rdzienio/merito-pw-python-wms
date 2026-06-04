""" autor: Robert Dzienio
    Aplikacja konsolowa do zarządzania magazynem typu WMS w Pythonie.
    Funkcjonalności:
    1. Produkty (dodawanie, edycja, usuwanie), 
    2. Lokalizacje magazynowe (regały, strefy), 
    3. Przyjęcia towaru (PZ), 
    4. Wydania towaru (WZ), 
    5. Raporty / statystyki
"""


import contextlib
import uuid # do generowania unikalnych identyfikatorów produktów
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional 
from pydantic import BaseModel, Field, field_validator, model_validator

# Model danych wejściowych z walidacją i transformacją danych.
class ProductInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    sku: str = Field(pattern=r'^[A-Z0-9\-]+$') # SKU - identyfikator produktu, np. "PROD-001"
    quantity: int = Field(ge=0)
    price: float = Field(gt=0)
 
    @field_validator('sku')
    @classmethod # transformacja SKU do wielkich liter, aby zapewnić spójność danych
    def sku_upper(cls, v: str) -> str:
        return v.upper()
    
class LocationInput(BaseModel):
    zone: str = Field(min_length=1, max_length=10)
    rack: int = Field(ge=1, le=999)
    shelf: int = Field(ge=1, le=99)
    capacity: int = Field(ge=1)
 
    @model_validator(mode='after')
    def check_label_unique_format(self) -> 'LocationInput':
        # dodatkowa walidacja krzyżowa
        if self.rack > 100 and self.shelf > 50:
            raise ValueError("Zbyt wysoka kombinacja rack/shelf — fizycznie niemożliwa")
        return self
    
class DocumentInput(BaseModel):
    sku: str
    quantity: int = Field(gt=0)
    location_label: str


@dataclass
class Product:
    name: str
    sku: str
    quantity: int
    price: float
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
 
    @staticmethod
    def generate_sku(name: str) -> str:
        # Metoda statyczna
        return name.upper().replace(" ", "-")[:12]
 
    @classmethod
    def from_input(cls, data: ProductInput) -> 'Product':
        # Metoda klasowa - alternatywny konstruktor.
        return cls(
            name=data.name,
            sku=data.sku,
            quantity=data.quantity,
            price=data.price,
        )
 
    def total_value(self) -> float:
        return self.quantity * self.price
 
    def __str__(self) -> str:
        return f"[{self.sku}] {self.name} | qty: {self.quantity} | cena: {self.price:.2f} zł"

@dataclass
class Location:
    zone: str
    rack: int
    shelf: int
    capacity: int
    stored_sku: Optional[str] = None
    stored_qty: int = 0
 
    @property
    def label(self) -> str:
        return f"{self.zone}-R{self.rack:03d}-S{self.shelf:02d}"
 
    @property
    def is_empty(self) -> bool:
        return self.stored_sku is None
 
    @property
    def free_space(self) -> int:
        return self.capacity - self.stored_qty
 
    def __str__(self) -> str:
        status = f"{self.stored_sku} ({self.stored_qty})" if self.stored_sku else "pusta"
        return f"{self.label} | pojemność: {self.capacity} | {status}"
 
 
@dataclass
class DocumentLine:
    sku: str
    quantity: int
    location_label: str

@dataclass
class WarehouseDocument:
    doc_type: str           # 'PZ' lub 'WZ'
    lines: list[DocumentLine]
    created_at: datetime = field(default_factory=datetime.now)
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
 
    def __str__(self) -> str:
        lines_str = ", ".join(f"{l.sku}×{l.quantity}" for l in self.lines)
        return f"{self.doc_type}/{self.id} @ {self.created_at:%Y-%m-%d %H:%M} | {lines_str}"

# Abstrakcyjne repozytorium - interfejs do zarządzania danymi, np. produkty, lokalizacje, dokumenty.    
class Repository(ABC):
 
    @abstractmethod
    def add(self, item) -> None: ...
 
    @abstractmethod
    def get(self, key: str): ...
 
    @abstractmethod
    def all(self) -> list: ...
 
    @abstractmethod
    def remove(self, key: str) -> bool: ...

class ProductRepository(Repository):
    def __init__(self):
        self._store: dict[str, Product] = {}
 
    def add(self, product: Product) -> None:
        self._store[product.sku] = product
 
    def get(self, sku: str) -> Optional[Product]:
        return self._store.get(sku)
 
    def all(self) -> list[Product]:
        return list(self._store.values())
 
    def remove(self, sku: str) -> bool:
        if sku in self._store:
            del self._store[sku]
            return True
        return False
 
    def update_quantity(self, sku: str, delta: int) -> bool:
        product = self.get(sku)
        if not product:
            return False
        new_qty = product.quantity + delta
        if new_qty < 0:
            return False
        product.quantity = new_qty
        return True
 
 
class LocationRepository(Repository):
    def __init__(self):
        self._store: dict[str, Location] = {}
 
    def add(self, location: Location) -> None:
        self._store[location.label] = location
 
    def get(self, label: str) -> Optional[Location]:
        return self._store.get(label)
 
    def all(self) -> list[Location]:
        return list(self._store.values())
 
    def remove(self, label: str) -> bool:
        if label in self._store:
            del self._store[label]
            return True
        return False
 
 
class DocumentRepository(Repository):
    def __init__(self):
        self._store: dict[str, WarehouseDocument] = {}
 
    def add(self, doc: WarehouseDocument) -> None:
        self._store[doc.id] = doc
 
    def get(self, doc_id: str) -> Optional[WarehouseDocument]:
        return self._store.get(doc_id)
 
    def all(self) -> list[WarehouseDocument]:
        return list(self._store.values())
 
    def remove(self, doc_id: str) -> bool:
        if doc_id in self._store:
            del self._store[doc_id]
            return True
        return False



# Prosty context manager symulujący transakcję.
@contextlib.contextmanager
def warehouse_transaction(description: str):
    print(f"  START transaction: {description}")
    try:
        yield
        print(f"  COMMIT: {description}")
    except Exception as exc:
        print(f"  ROLLBACK: {description} — błąd: {exc}")
        raise    

# SERWIS — logika biznesowa (kompozycja repozytoriów)
class WarehouseService: 
    def __init__(self):
        self.products = ProductRepository()
        self.locations = LocationRepository()
        self.documents = DocumentRepository()
 
    # Produkty
 
    def add_product(self, data: ProductInput) -> Product:
        if self.products.get(data.sku):
            raise ValueError(f"Produkt {data.sku} już istnieje")
        product = Product.from_input(data)
        self.products.add(product)
        return product
 
    def edit_product(self, sku: str, **kwargs) -> Product:
        product = self.products.get(sku)
        if not product:
            raise KeyError(f"Nie znaleziono produktu {sku}")
        for k, v in kwargs.items():
            if hasattr(product, k):
                setattr(product, k, v)
        return product
 
    def remove_product(self, sku: str) -> bool:
        return self.products.remove(sku)
 
    # Lokalizacje
 
    def add_location(self, data: LocationInput) -> Location:
        loc = Location(
            zone=data.zone,
            rack=data.rack,
            shelf=data.shelf,
            capacity=data.capacity,
        )
        if self.locations.get(loc.label):
            raise ValueError(f"Lokalizacja {loc.label} już istnieje")
        self.locations.add(loc)
        return loc
 
    # Dokumenty: PZ / WZ
 
    def receive_goods(self, doc_input: DocumentInput) -> WarehouseDocument:
        # PZ — przyjęcie towaru na lokalizację.
        with warehouse_transaction(f"PZ {doc_input.sku} ×{doc_input.quantity}"):
            product = self.products.get(doc_input.sku)
            if not product:
                raise KeyError(f"Nieznany SKU: {doc_input.sku}")
 
            location = self.locations.get(doc_input.location_label)
            if not location:
                raise KeyError(f"Nieznana lokalizacja: {doc_input.location_label}")
 
            if location.free_space < doc_input.quantity:
                raise ValueError(f"Za mało miejsca: {location.free_space} < {doc_input.quantity}")
 
            self.products.update_quantity(doc_input.sku, +doc_input.quantity)
            location.stored_sku = doc_input.sku
            location.stored_qty += doc_input.quantity
 
            doc = WarehouseDocument(
                doc_type='PZ',
                lines=[DocumentLine(doc_input.sku, doc_input.quantity, doc_input.location_label)]
            )
            self.documents.add(doc)
            return doc
 
    def issue_goods(self, doc_input: DocumentInput) -> WarehouseDocument:
        # WZ — wydanie towaru z lokalizacji.
        with warehouse_transaction(f"WZ {doc_input.sku} ×{doc_input.quantity}"):
            product = self.products.get(doc_input.sku)
            if not product:
                raise KeyError(f"Nieznany SKU: {doc_input.sku}")
 
            location = self.locations.get(doc_input.location_label)
            if not location:
                raise KeyError(f"Nieznana lokalizacja: {doc_input.location_label}")
 
            if location.stored_sku != doc_input.sku:
                raise ValueError(f"Na lokalizacji {location.label} nie ma {doc_input.sku}")
 
            if location.stored_qty < doc_input.quantity:
                raise ValueError(f"Za mało towaru: {location.stored_qty} < {doc_input.quantity}")
 
            self.products.update_quantity(doc_input.sku, -doc_input.quantity)
            location.stored_qty -= doc_input.quantity
            if location.stored_qty == 0:
                location.stored_sku = None
 
            doc = WarehouseDocument(
                doc_type='WZ',
                lines=[DocumentLine(doc_input.sku, doc_input.quantity, doc_input.location_label)]
            )
            self.documents.add(doc)
            return doc
 
    # Raporty
 
    def report_stock(self) -> list[Product]:
        return sorted(
            self.products.all(),
            key=lambda p: (-p.total_value(), p.name)
        )
 
    def report_low_stock(self, threshold: int = 5) -> list[Product]:
        return [p for p in self.products.all() if p.quantity <= threshold]
 
    def report_empty_locations(self) -> list[Location]:
        return sorted(
            filter(lambda loc: loc.is_empty, self.locations.all()),
            key=lambda loc: loc.label
        )
 
    def report_total_value(self) -> float:
        return sum(p.total_value() for p in self.products.all())
 
    def report_documents(self, doc_type: Optional[str] = None) -> list[WarehouseDocument]:
        # Historia dokumentów, opcjonalnie przefiltrowana po typie.
        docs = self.documents.all()
        if doc_type:
            docs = [d for d in docs if d.doc_type == doc_type]
        return sorted(docs, key=lambda d: d.created_at, reverse=True)


# users

def _prompt(label: str, cast=str, default=None):
    # Pomocnicza funkcja odczytu z konsoli.
    raw = input(f"  {label}: ").strip()
    if not raw and default is not None:
        return default
    return cast(raw)

class User(ABC):
    def __init__(self, login: str, password: str, role: str):
        self.login = login
        self._password = password
        self.role = role
 
    def authenticate(self, password: str) -> bool:
        return self._password == password
 
    @abstractmethod
    def menu(self, wms: WarehouseService) -> None: ...
 
    def __str__(self) -> str:
        return f"{self.login} ({self.role})"
 

 # Pracownik magazynu - przyjmuje i wydaje towar, przegląda lokalizacje.
class Worker(User):
    def __init__(self, login: str, password: str):
        super().__init__(login, password, "Worker")
 
    def menu(self, wms: WarehouseService) -> None:
        while True:
            print(f"\nMenu magazyniera ({self.login}):")
            print("  1. Lista produktów")
            print("  2. Lista lokalizacji")
            print("  3. Przyjęcie towaru (PZ)")
            print("  4. Wydanie towaru (WZ)")
            print("  0. Wyloguj")
 
            choice = input("> ").strip()
 
            if choice == "1":
                wms.show_products()
            elif choice == "2":
                wms.show_locations()
            elif choice == "3":
                wms.do_receive_goods()
            elif choice == "4":
                wms.do_issue_goods()
            elif choice == "0":
                print("Wylogowano!\n")
                return
            else:
                print("Nieznana opcja, spróbuj ponownie.\n")


# Kierownik magazynu - pełen dostęp: produkty, lokalizacje, raporty.

class Manager(User):

    def __init__(self, login: str, password: str):
        super().__init__(login, password, "Kierownik")
 
    def menu(self, wms: WarehouseService) -> None:
        while True:
            print(f"\nMenu kierownika ({self.login}):")
            print("  1. Zarządzaj produktami")
            print("  2. Zarządzaj lokalizacjami")
            print("  3. Przyjęcie towaru (PZ)")
            print("  4. Wydanie towaru (WZ)")
            print("  5. Raporty")
            print("  0. Wyloguj")
 
            choice = input("> ").strip()
 
            if choice == "1":
                wms.manage_products()
            elif choice == "2":
                wms.manage_locations()
            elif choice == "3":
                wms.do_receive_goods()
            elif choice == "4":
                wms.do_issue_goods()
            elif choice == "5":
                wms.show_reports()
            elif choice == "0":
                print("Wylogowano!\n")
                return
            else:
                print("Nieznana opcja, spróbuj ponownie.\n") 

class Warehouse:
 
    def __init__(self):
        self._svc = WarehouseService()
        self._users: list[User] = []
 
    def add_user(self, user: User) -> None:
        self._users.append(user)
 
    # produkty
 
    def show_products(self) -> None:
        products = self._svc.products.all()
        print("\nLista produktów:")
        if not products:
            print("  (brak produktów)")
        for i, p in enumerate(products, 1):
            print(f"  {i}. {p}")
 
    def manage_products(self) -> None:
        while True:
            print("\nZarządzanie produktami:")
            print("  1. Dodaj produkt")
            print("  2. Edytuj produkt")
            print("  3. Usuń produkt")
            print("  4. Lista produktów")
            print("  0. Wstecz")
 
            choice = input("> ").strip()
 
            if choice == "1":
                try:
                    data = ProductInput(
                        name=_prompt("Nazwa"),
                        sku=_prompt("SKU (np. APPLE-01)"),
                        quantity=_prompt("Ilość", int),
                        price=_prompt("Cena", float),
                    )
                    p = self._svc.add_product(data)
                    print(f"  Dodano: {p}")
                except Exception as e:
                    print(f"  Błąd: {e}")
 
            elif choice == "2":
                sku = _prompt("SKU do edycji").upper()
                field_name = _prompt("Pole (name/quantity/price)")
                new_val = _prompt("Nowa wartość")
                try:
                    cast = {"quantity": int, "price": float}.get(field_name, str)
                    self._svc.edit_product(sku, **{field_name: cast(new_val)})
                    print(f"  Zaktualizowano {sku}")
                except Exception as e:
                    print(f"  Błąd: {e}")
 
            elif choice == "3":
                sku = _prompt("SKU do usunięcia").upper()
                ok = self._svc.remove_product(sku)
                print(f"  {'Usunięto' if ok else 'Nie znaleziono'} {sku}")
 
            elif choice == "4":
                self.show_products()
 
            elif choice == "0":
                return
            else:
                print("Nieznana opcja, spróbuj ponownie.\n")
 
    # lokalizacje
 
    def show_locations(self) -> None:
        locs = self._svc.locations.all()
        print("\nLokalizacje:")
        if not locs:
            print("  (brak lokalizacji)")
        for i, loc in enumerate(sorted(locs, key=lambda l: l.label), 1):
            print(f"  {i}. {loc}")
 
    def manage_locations(self) -> None:
        while True:
            print("\nZarządzanie lokalizacjami:")
            print("  1. Dodaj lokalizację")
            print("  2. Lista lokalizacji")
            print("  0. Wstecz")
 
            choice = input("> ").strip()
 
            if choice == "1":
                try:
                    data = LocationInput(
                        zone=_prompt("Strefa (np. A)").upper(),
                        rack=_prompt("Regał nr", int),
                        shelf=_prompt("Półka nr", int),
                        capacity=_prompt("Pojemność (szt.)", int),
                    )
                    loc = self._svc.add_location(data)
                    print(f"  Dodano: {loc}")
                except Exception as e:
                    print(f"  Błąd: {e}")
 
            elif choice == "2":
                self.show_locations()
 
            elif choice == "0":
                return
            else:
                print("Nieznana opcja, spróbuj ponownie.\n")
 
    # dokumenty

    def do_receive_goods(self) -> None:
        print("\nPrzyjęcie towaru (PZ):")
        try:
            data = DocumentInput(
                sku=_prompt("SKU").upper(),
                quantity=_prompt("Ilość", int),
                location_label=_prompt("Lokalizacja (np. A-R001-S01)").upper(),
            )
            doc = self._svc.receive_goods(data)
            print(f"  Wystawiono: {doc}")
        except Exception as e:
            print(f"  Błąd: {e}")
 
    def do_issue_goods(self) -> None:
        print("\nWydanie towaru (WZ):")
        try:
            data = DocumentInput(
                sku=_prompt("SKU").upper(),
                quantity=_prompt("Ilość", int),
                location_label=_prompt("Lokalizacja (np. A-R001-S01)").upper(),
            )
            doc = self._svc.issue_goods(data)
            print(f"  Wystawiono: {doc}")
        except Exception as e:
            print(f"  Błąd: {e}")
 
    # raporty
 
    def show_reports(self) -> None:
        while True:
            print("\nRaporty:")
            print("  1. Stan magazynu (wg wartości)")
            print("  2. Niski stan (≤ 5 szt.)")
            print("  3. Puste lokalizacje")
            print("  4. Łączna wartość magazynu")
            print("  5. Historia dokumentów")
            print("  0. Wstecz")
 
            choice = input("> ").strip()
 
            if choice == "1":
                print("\nStan magazynu:")
                for p in self._svc.report_stock():
                    print(f"  {p}  | wartość: {p.total_value():.2f} zł")
 
            elif choice == "2":
                low = self._svc.report_low_stock()
                print(f"\nProdukty z qty ≤ 5 ({len(low)}):")
                for p in low:
                    print(f"  {p}")
 
            elif choice == "3":
                empty = self._svc.report_empty_locations()
                print(f"\nPuste lokalizacje ({len(empty)}):")
                for loc in empty:
                    print(f"  {loc}")
 
            elif choice == "4":
                total = self._svc.report_total_value()
                print(f"\nŁączna wartość magazynu: {total:,.2f} zł")
 
            elif choice == "5":
                doc_type = _prompt("Typ (PZ/WZ/Enter=wszystkie)", default="")
                docs = self._svc.report_documents(doc_type.upper() or None)
                print(f"\nDokumenty ({len(docs)}):")
                if not docs:
                    print("  (brak)")
                for d in docs:
                    print(f"  {d}")
 
            elif choice == "0":
                return
            else:
                print("Nieznana opcja, spróbuj ponownie.\n")
 
    # logowanie
 
    def log_in(self) -> Optional[User]:
        max_attempts = 3
        print("\n----- LOGOWANIE -----")
        for attempt in range(1, max_attempts + 1):
            login = input("Login: ").strip()
            password = input("Hasło: ").strip()
            for user in self._users:
                if user.login == login and user.authenticate(password):
                    print(f"\nZalogowano: {user}!\n")
                    return user
            print(f"Błędny login lub hasło! Próba {attempt}/{max_attempts}\n")
        print("Przekroczono liczbę prób! Do widzenia.")
        return None
 
    # załaduj wstepne dane
 
    def seed_demo_data(self) -> None:
        products = [
            ProductInput(name="Jabłko Gala 1kg", sku="OW-JAB-GALA", quantity=100, price=2.50),
            ProductInput(name="Mlekpol Mazurski Smak Masło ekstra 200g", sku="MAS-MAZ-MLEK-200G", quantity=0, price=3.50),
            ProductInput(name="Sok Pomarańczowy TYMBARK karton 1l", sku="SOK-POM-TYM-K1L", quantity=50, price=4.99),
            ProductInput(name="Coca-Cola Napój gazowany 1.5l", sku="COCACOLA-15L", quantity=50, price=6.99),
            ProductInput(name="Mleko Łaciate UHT MLEKOVITA 3.2% karton 1l", sku="ML-UHT-MLEK-32-K1L", quantity=50, price=3.20),
            ProductInput(name="Ser Gouda kostka MLEKOVITA 200g", sku="SER-GOU-MLEK-K200", quantity=0, price=18.00),
        ]
        for p in products:
            self._svc.add_product(p)
 
        locations = [
            LocationInput(zone="A", rack=1, shelf=1, capacity=200),
            LocationInput(zone="A", rack=1, shelf=2, capacity=200),
            LocationInput(zone="A", rack=2, shelf=1, capacity=200),
            LocationInput(zone="A", rack=2, shelf=2, capacity=200),
            LocationInput(zone="B", rack=1, shelf=1, capacity=50),
            LocationInput(zone="B", rack=1, shelf=2, capacity=50),
            LocationInput(zone="B", rack=2, shelf=1, capacity=50),
            LocationInput(zone="B", rack=2, shelf=2, capacity=50),
            LocationInput(zone="C", rack=1, shelf=1, capacity=300),
            LocationInput(zone="C", rack=2, shelf=1, capacity=300),
        ]
        for loc in locations:
            self._svc.add_location(loc)
 
        self._svc.receive_goods(DocumentInput(sku="OW-JAB-GALA", quantity=100, location_label="C-R001-S01"))
        self._svc.receive_goods(DocumentInput(sku="ML-UHT-MLEK-32-K1L", quantity=50, location_label="A-R001-S02"))
        self._svc.receive_goods(DocumentInput(sku="SOK-POM-TYM-K1L", quantity=50, location_label="B-R002-S01"))
        self._svc.receive_goods(DocumentInput(sku="COCACOLA-15L", quantity=50, location_label="B-R002-S02"))
        print("Dane demo załadowane.\n")
 
def main() -> None:
    warehouse = Warehouse()
 
    warehouse.add_user(Manager("admin",    "admin"))
    warehouse.add_user(Manager("kierownik", "321321"))
    warehouse.add_user(Worker("dzienro",     "123123"))
    warehouse.add_user(Worker("kowalski",    "abc123"))
    warehouse.seed_demo_data()
 
    print("╔══════════════════════════════════════════╗")
    print("║  WMS (nie SAP EWM) - Magazyn konsolowy   ║")
    print("╚══════════════════════════════════════════╝")

 
    while True:
        print("\nWitaj w systemie WMS!")
        print("  1. Zaloguj")
        print("  0. Wyjście")
 
        choice = input("> ").strip()
 
        if choice == "1":
            user = warehouse.log_in()
            if user is None:
                return
            user.menu(warehouse)
        elif choice == "0":
            print("Do widzenia!")
            break
        else:
            print("Nieprawidłowa opcja.\n")
 
 
if __name__ == "__main__":
    main()                