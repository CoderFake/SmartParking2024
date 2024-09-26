from typing import Any, Union
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaMode, JsonSchemaValue
from pydantic_core import CoreSchema


class SelfContainedGenerateSchema(GenerateJsonSchema):
    """
    A schema generation extension class that transforms nested JSON schemas generated from Pydantic BaseModels
    into a hierarchical structure without references.
    """

    def generate(
        self, schema: CoreSchema, mode: JsonSchemaMode = 'validation'
    ) -> JsonSchemaValue:
        js = super().generate(schema, mode)

        if '$defs' not in js:
            return js

        defs = js.pop('$defs')

        prefix = '#/$defs/'

        def walk(
            v: Union[list[Any], dict[str, Any], Any], memo: set[str]
        ) -> Any:
            if isinstance(v, list):
                return [walk(i, memo) for i in v]
            elif isinstance(v, dict):
                if "$ref" in v:
                    key = v["$ref"][len(prefix):]
                    if key in memo:
                        return {}
                    ref = defs[key]
                    memo = set(memo)
                    ref = walk(ref, memo)
                    return ref
                else:
                    return {k: walk(u, memo) for k, u in v.items()}
            else:
                return v

        js = walk(js, set())

        return js  # type: ignore
