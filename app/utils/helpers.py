from typing import Union, List
from bson import ObjectId


def fix_id(document: Union[dict, List[dict]]) -> Union[dict, List[dict], None]:
    def _convert(doc):
        if not doc:
            return None
        doc = dict(doc)  # Make a shallow copy to avoid side-effects
        doc["id"] = str(doc.pop("_id", None))
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                doc[key] = str(value)
        return doc

    if isinstance(document, list):
        return [_convert(doc) for doc in document]
    return _convert(document)
