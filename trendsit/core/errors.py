"""공통 예외. llm·images가 서로를 가져오지 않고 같은 계열을 쓰도록 따로 둔다."""


class LLMError(Exception):
    pass
