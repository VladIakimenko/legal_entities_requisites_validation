import re
from dataclasses import asdict, fields, dataclass

# Lamb Framework
from lamb.exc import InvalidParamValueError

# Project
from api.models import PartnerType


@dataclass
class Requisites:
    def check_fields(self, data: dict) -> None:
        for field in fields(type(self)):
            expected_type = field.type
            if not isinstance(data[field.name], expected_type):
                raise TypeError(
                    f"{self.__class__.__name__} '{field.name}' "
                    f"field expected type is '{expected_type}', got '{type(data[field.name])}'"
                )

    def check_values(self) -> None:
        for method_name in dir(self):
            if method_name.startswith("validate_"):
                method = getattr(self, method_name)
                if callable(method):
                    is_valid, message = method()
                    if not is_valid:
                        raise ValueError(f"Validation failed: {message}")

    @classmethod
    def from_dict(cls, data: dict) -> "Requisites":
        keys_to_allow_spaces = [
            "real_address",
            "legal_address",
            "short_entity_name",
            "full_entity_name",
            "bank_name",
        ]
        cleaned_data = {
            key: value.replace(" ", "") if isinstance(value, str) and key not in keys_to_allow_spaces else value
            for key, value in data.items()
        }

        instance = cls(**cleaned_data)
        instance.check_fields(data)
        instance.check_values()
        return instance

    @classmethod
    def validate(cls, data: dict) -> dict:
        """
        Validates the incoming requisites dictionary, by converting it into a data class instance,
        calling available validation methods and then converting it back into a valid requisites' dictionary.
        Raises InvalidParamValueError, if validation fails.

        usage example:
        ```
        validated_requisites: dict = CommonRequisites.validate(raw_private_individual_requisites)
        validated_requisites: dict = LegalEntityRequisites.validate(raw_legal_entity_requisites)
        validated_requisites: dict = IPRequisites.validate(raw_ip_requisites)
        ```
        """
        try:
            instance = cls.from_dict(data)
            valid_data_dict = asdict(instance)
        except (ValueError, TypeError) as e:
            raise InvalidParamValueError(f"Validation error: {e}")

        return valid_data_dict


@dataclass
class CommonRequisites(Requisites):
    """
    validates PRIVATE_INDIVIDUAL
    """

    requisites_type: str
    requisites_name: str
    requisites_patronymic: str
    requisites_surname: str
    real_address: str
    inn: str
    bik: str
    bank_name: str
    correspondent_account: str
    bank_account: str

    def validate_inn(self) -> (bool, str):
        if not self.inn.isdigit():
            return False, "INN must only contain numbers."

        if not (1 <= int(self.inn[:2]) <= 92) and not self.inn.startswith("9909"):
            return False, "INN has invalid leading digits."

        # legal entities
        if self.requisites_type in [PartnerType.OOO, PartnerType.AO, PartnerType.PAO, PartnerType.ZAO]:
            if len(self.inn) != 10:
                return False, "INN for legal entities must be 10 digits long."

            # Check control number
            coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
            control_sum = sum([int(self.inn[i]) * coefficients[i] for i in range(9)])
            if int(self.inn[-1]) != control_sum % 11 % 10:
                return False, "INN has incorrect control number for a legal entity."

        # private individuals and IP
        elif self.requisites_type in [PartnerType.IP, PartnerType.PRIVATE_INDIVIDUAL]:
            if len(self.inn) != 12:
                return False, "INN for private individuals or IP must be 12 digits long."

            # Check control numbers
            coefficients_11 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
            control_sum_11 = sum([int(self.inn[i]) * coefficients_11[i] for i in range(10)])
            if int(self.inn[10]) != control_sum_11 % 11 % 10:
                return False, "INN has incorrect control number for the 11th digit of private individual or IP."

            coefficients_12 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
            control_sum_12 = sum([int(self.inn[i]) * coefficients_12[i] for i in range(11)])
            if int(self.inn[11]) != control_sum_12 % 11 % 10:
                return False, "INN has incorrect control number for the 12th digit of private individual or IP."

        return True, ""

    def validate_bik(self) -> (bool, str):
        if not self.bik.isdigit():
            return False, "BIK must only contain numbers."

        if len(self.bik) != 9:
            return False, "BIK must be 9 digits long."

        if self.bik[:2] != "04":
            return False, "BIK first 2 digits must be '04'."

        if not (50 <= int(self.bik[6:]) <= 999):
            return False, "BIK last 3 digits should be within 050 to 999."

        return True, ""

    def validate_bank_account(self) -> (bool, str):
        if not self.bank_account.isdigit():
            return False, "Bank account can only consist of digits."

        if len(self.bank_account) != 20:
            return False, "Bank account must consist of 20 digits."

        # check control number
        combined_number = self.bik[-3:] + self.bank_account
        coefficients = [7, 1, 3] * 7 + [7, 1]
        checksum = sum((coefficient * int(digit)) % 10 for coefficient, digit in zip(coefficients, combined_number))

        if checksum % 10 == 0:
            return True, ""
        else:
            return False, "Bank account has incorrect control number."

    def validate_correspondent_account(self) -> (bool, str):
        if not self.correspondent_account.isdigit():
            return False, "Correspondent account can only consist of digits."

        if len(self.correspondent_account) != 20:
            return False, "Correspondent account must consist of 20 digits."

        # Check control number
        combined_number = "0" + self.bik[4:6] + self.correspondent_account
        coefficients = [7, 1, 3] * 7 + [7, 1]
        checksum = sum(coefficient * int(digit) for coefficient, digit in zip(coefficients, combined_number))

        if checksum % 10 == 0:
            return True, ""
        else:
            return False, "Correspondent account has incorrect control number."


@dataclass
class EntityCommonRequisites(CommonRequisites):
    short_entity_name: str
    full_entity_name: str
    legal_address: str
    okved: str
    okpo: str
    okato: str

    def validate_okato(self) -> (bool, str):
        if not self.okato.isdigit():
            return False, "OKATO must only contain digits."

        if not (8 <= len(self.okato) <= 11):
            return False, "OKATO must be from 8 to 11 digits long."

        return True, ""

    def validate_okpo(self) -> (bool, str):
        if not self.okpo.isdigit():
            return False, "OKPO must only contain digits."

        if len(self.okpo) not in (8, 10):
            return False, "OKPO must be either 8 or 10 digits long."

        return True, ""

    def validate_okved(self) -> (bool, str):
        okved = self.okved.split('.')
        if not all(part.isdigit() for part in okved):
            return False, "OKVED must only contain digits separated by '.'"

        if not 2 <= len(''.join(okved)) <= 6:
            return False, "OKVED must contain from 2 to 6 digits in total."

        if not all(1 <= len(part) <= 2 for part in okved):
            return False, "Each part of OKVED separated by '.' must contain one or two digits."

        return True, ""


@dataclass
class IPRequisites(EntityCommonRequisites):
    """
    validates IP
    """

    ogrnip: str

    def validate_ogrnip(self) -> (bool, str):
        if not self.ogrnip.isdigit():
            return False, "OGRNIP must only contain digits."

        if len(self.ogrnip) != 15:
            return False, "OGRNIP must be 15 digits long."

        if self.ogrnip[0] == "0":
            return False, "OGRNIP cannot start with zero."

        # Check control number
        control_number = int(str(int(self.ogrnip[:-1]) % 13)[-1])
        if control_number != int(self.ogrnip[-1]):
            return False, "OGRNIP has invalid control number."

        return True, ""


@dataclass
class LegalEntityRequisites(EntityCommonRequisites):
    """
    validates OOO, AO, PAO, ZAO
    """

    ogrn: str
    kpp: str

    def validate_kpp(self) -> (bool, str):
        if len(self.kpp) != 9:
            return False, "KPP must be of 9 chars (digits or latin capital letters)"

        pattern = re.compile(r"^[0-9]{4}[0-9A-Z]{2}[0-9]{3}$")
        if not pattern.match(self.kpp):
            return False, "KPP has incorrect pattern."

        return True, "KPP is valid."

    def validate_ogrn(self) -> (bool, str):
        if not self.ogrn.isdigit():
            return False, "OGRN must only contain digits."

        if len(self.ogrn) != 13:
            return False, "OGRN must be 13 digits long."

        if self.ogrn[0] == "0":
            return False, "OGRN cannot start with a zero."

        # Check control number
        control_number = int(str(int(self.ogrn[:-1]) % 11)[-1])
        if control_number != int(self.ogrn[-1]):
            return False, "OGRN has invalid control number."

        return True, ""


requisites_validators_map = {
    "OOO": LegalEntityRequisites,
    "AO": LegalEntityRequisites,
    "ZAO": LegalEntityRequisites,
    "PAO": LegalEntityRequisites,
    "IP": IPRequisites,
    "PRIVATE_INDIVIDUAL": CommonRequisites,
}
