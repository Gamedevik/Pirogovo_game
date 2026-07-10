from pydantic import BaseModel, field_validator


class UserCreate(BaseModel):
    username: str
    email: str
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Имя должно быть не короче 3 символов")
        if len(v) > 32:
            raise ValueError("Имя слишком длинное (макс. 32 символа)")
        return v

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        v = v.strip().lower()
        # Простая проверка без внешних зависимостей (email-validator не нужен).
        if "@" not in v or "." not in v.split("@")[-1] or len(v) < 5:
            raise ValueError("Некорректный email")
        return v

    @field_validator("password")
    @classmethod
    def password_valid(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Пароль должен быть не короче 6 символов")
        if len(v.encode("utf-8")) > 256:
            raise ValueError("Пароль слишком длинный")
        return v
