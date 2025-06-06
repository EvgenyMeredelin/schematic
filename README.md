## __Отчет о принятых решениях__

1. Обработчики файлов, отвечающие за построение схем, будучи наследниками базового абстрактного класса, реализующего общую функциональность, обязаны определить свой целевой тип содержимого и то, каким образом из содержимого формируется _референсный объект_ — объект, на основе которого, как по образцу, будет построена схема. В работе созданы обработчики для JSON и XML. При этом случай с XML сводится к JSON, что выгодно унификацией интерфейса построения схем, их сравнения и извлечения полей.

2. Нам интересно хранить только уникальные, ранее не встречавшиеся, схемы. Это делает необходимым реализовать способ их сравнения. Использованная в работе идея следующая. В извлеченной JSON-схеме рекурсивно сортируются все вложенные объекты — ключи и соответствующие им [нестроковые] поля-коллекции. Результат сериализуется и от него считается детерминированный хеш. Так одинаковые схемы (равные словари) дадут на выходе одинаковые дайджесты, которые также удобно использовать как уникальные идентификаторы схем.

3. При запуске приложения на сервере (в этой работе это виртуальная машина на Cloud.ru) интроспекцией кода собирается [динамический] маппинг между типом содержимого файла и ответственным за него хендлером из п.1, объект которого инициализируется содержимым загружаемого документа. Если идентифицированная по дайджесту, как было сказано в п.2, схема ранее не встречалась, она регистрируется в базе данных: на каждое [уникальное] поле схемы в таблицу базы данных вносится запись вида _(дата, тип содержимого, дайджест, поле)_. Таблица хранит лишь соответствие между полем схемы и ее идентификатором, а сама схема как JSON-документ загружается в бакет хранилища S3: _дайджест схемы = идентификатор схемы в базе данных = имя файла в S3_.

Пример работы эндпоинта `/file`, отвечающего за извлечение схемы из загружаемого файла (с помощью HTTPie):
```
$ . .env
$ http -f POST $HOST:$PORT/file file@task/complex_data_final.json

HTTP/1.1 200 OK
content-length: 1862
content-type: application/json
date: Tue, 27 May 2025 12:59:41 GMT
server: uvicorn

{
    "content_type": "application/json",
    "fields": [
        "category",
        "city",
        "coordinates",
        "country",
        "created_at",
        "currency",
        "employees",
        "financials",
        "id",
        "industry",
        "is_active",
        "last_sale_date",
        "last_year_growth",
        "latitude",
        "location",
        "longitude",
        "metadata",
        "name",
        "price",
        "product_id",
        "products",
        "profit_margin",
        "revenue",
        "stock",
        "tags",
        "updated_at"
    ],
    "filename": "complex_data_final.json",
    "schema": {
        "$schema": "http://json-schema.org/schema#",
        "items": {
            "properties": {
                "employees": {
                    "type": "integer"
                },
                "financials": {
                    "properties": {
                        "currency": {
                            "type": "string"
                        },
                        "last_year_growth": {
                            "type": "number"
                        },
                        "profit_margin": {
                            "type": "number"
                        },
                        "revenue": {
                            "type": "number"
                        }
                    },
                    "required": [
                        "currency",
                        "last_year_growth",
                        "profit_margin",
                        "revenue"
                    ],
                    "type": "object"
                },
                "id": {
                    "type": "string"
                },
                "industry": {
                    "type": "string"
                },
                "location": {
                    "properties": {
                        "city": {
                            "type": "string"
                        },
                        "coordinates": {
                            "properties": {
                                "latitude": {
                                    "type": "number"
                                },
                                "longitude": {
                                    "type": "number"
                                }
                            },
                            "required": [
                                "latitude",
                                "longitude"
                            ],
                            "type": "object"
                        },
                        "country": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "city",
                        "coordinates",
                        "country"
                    ],
                    "type": "object"
                },
                "metadata": {
                    "properties": {
                        "created_at": {
                            "type": "string"
                        },
                        "is_active": {
                            "type": "boolean"
                        },
                        "tags": {
                            "items": {
                                "type": "string"
                            },
                            "type": "array"
                        },
                        "updated_at": {
                            "type": "string"
                        }
                    },
                    "required": [
                        "created_at",
                        "is_active",
                        "tags",
                        "updated_at"
                    ],
                    "type": "object"
                },
                "name": {
                    "type": "string"
                },
                "products": {
                    "items": {
                        "properties": {
                            "category": {
                                "type": "string"
                            },
                            "last_sale_date": {
                                "type": "string"
                            },
                            "name": {
                                "type": "string"
                            },
                            "price": {
                                "type": "number"
                            },
                            "product_id": {
                                "type": "string"
                            },
                            "stock": {
                                "type": "integer"
                            }
                        },
                        "required": [
                            "category",
                            "last_sale_date",
                            "name",
                            "price",
                            "product_id",
                            "stock"
                        ],
                        "type": "object"
                    },
                    "type": "array"
                }
            },
            "required": [
                "employees",
                "financials",
                "id",
                "industry",
                "location",
                "metadata",
                "name",
                "products"
            ],
            "type": "object"
        },
        "type": "array"
    },
    "status": {
        "comment": "Just added by you.",
        "date_added": "2025-05-27T15:59:53.769771"
    }
}
```

При повторной отправке того же документа (документа с такой же схемой) мы увидим другой комментарий, но ту же метку времени, указывающую на момент оригинальной регистрации схемы выше:
```
{
    "content_type": "application/json",
    ...
    "status": {
        "comment": "Seen before.",
        "date_added": "2025-05-27T15:59:53.769771"
    }
}
```

4. Поиск схем осуществляется по принадлежащим им полям, как по ключевым словам, в двух логических режимах, `all` и `any` (по умолчанию), смысл которых соответствует встроенным функциям. `all` предполагает, что искомые поля должны быть подмножеством множества полей возвращаемой схемы (схем). Это в том числе допускает и равенство множеств. В этом режиме мы исходим из того, что пользователь ищет сочетание именно таких полей, и поэтому возвращаются схемы, содержащие поля с именно таким написанием.

Иначе работает режим `any`: в искомых полях исправляются, если есть, опечатки, поля дополняются синонимами и сравниваются с [уникальными] полями в базе данных по нормализованному расстоянию Левенштейна. Схема, хотя бы одно поле которой набирает по данной метрике значение не менее порогового, попадает в результаты: из бакета S3 достается документ с именем, равным дайджесту схемы, как описано в п.3. Пример работы эндпоинта `/search`:
```
$ http $HOST:$PORT/search fields==state fields==label

{
    "fields": [
        "state",
        "label"
    ],
    "logic": "any",
    "schemas": [
        {
            "$schema": "http://json-schema.org/schema#",
            ...
        }
    ],
    "similar_fields": [
        "country",
        "tags"
    ]
}
```
Прим. На момент, когда вы будете читать этот текст, приложение будет поднято (работает юнит `systemd`) и доступно для проверки, но база данных будет пуста — пожалуйста, воспользуйтесь загрузкой своих тестовых документов через `/file` перед поиском через `/search`. Из рута настроена переадресация на Swagger UI.

5. Понимаю, что задание выполнено не полностью и, скорее всего, не в полной мере соответствует вашим ожиданиям, но если оценивать работу со стороны, я бы дал сам себе шанс. Надеюсь, это же сделаете и вы. Спасибо за уделенное время!