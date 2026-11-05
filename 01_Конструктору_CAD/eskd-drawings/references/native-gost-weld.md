# Нативная сварная выноска ГОСТ: перенос из готовой КД

Проверено 10.10.2026 в SolidWorks 2025 SP3, API 33.3.0, на опорах ND2X4–6V. Источник подходящего символа — готовый чертёж опоры ND1X3–7R. Это способ переноса оформления аннотации, не доказательство одинаковой конструкции или применимости всех сварных требований аналога.

## Проверенный программный порядок

1. Сохранить старый SLDDRW/PDF в `_Аннулировано`. Открыть целевой чертёж в явно принадлежащем задаче CAD-сеансе. Получить **его собственное** ребро стыка и координаты наконечника в пространстве листа. Удалять только заменяемые аннотации и явно определённые устаревшие декоративные круги; размеры и исходную модель не менять.
2. Открыть готовый аналог без права сохранения. Выбрать его подходящий `IWeldSymbol.GetAnnotation()` через `Select3`, вызвать `EditCopy`, закрыть источник без сохранения. Целевой документ должен быть уже открыт: открытие нового документа между копированием и вставкой может сбросить внутренний буфер SolidWorks. Активировать целевой чертёж и нужный вид, затем `Paste`.
3. Выполнить **последовательно**:
   - `SetAttachedEntities(SAFEARRAY(IDispatch, own_edge))`;
   - `SetPosition2(text_x, text_y, z)`;
   - `SetLeaderAttachmentPointAtIndex(0, tip_x, tip_y, tip_z)`;
   - повторно `SetAttachedEntities(...own_edge...)`;
   - повторно `SetPosition2(...)`.

Явное назначение наконечника очищает старую геометрию линии из чужого вида, но переводит наконечник в свободную точку: после него привязку необходимо восстановить. Одного первого `SetAttachedEntities` недостаточно. При нескольких выносках обработать каждую и проверить их собственные рёбра; индекс 0 не является общим правилом.

4. Очистить выбор, перестроить, сохранить, закрыть и открыть SLDDRW. Проверить `GetAttachedEntityCount3`, `IsDangling`, `GetTextCount/GetTextAtIndex`, `GetLeaderPointsAtIndex`, `GetLineAtIndex`, `GetArcAtIndex`. Знак замкнутого контура расположен в перегибе полки; после переноса нет линий к прежнему листу. Размеры модели и чертежа сохранили значения.
5. Экспортировать нативный PDF и проверить весь лист и увеличенный фрагмент. Текст не перекрывает разрезные буквы, наконечник указывает на правильный стык, старые отдельные круги удалены. Подтвердить неизменность хеша готового источника.

## Ограничения проверенной версии

- `IWeldSymbol.SetText` работает с полями ISO; записанный текст может отсутствовать среди реально отображаемых надписей ГОСТ. Не принимать это по одному `True`.
- `IAnnotation.SaveStyle/LoadStyle/SetStyleName` вернули успех, но в испытании не восстановили текст ГОСТ. `SaveStyle` также добавил к переданному пути имя и расширение `.sldsfstl`. Такой стиль не утверждён для повторного использования. Файл не переименовывать ради видимости поддержки.
- У исходного ГОСТ-символа круг замкнутого контура реально присутствует в `GetArcAtIndex`, хотя `IWeldSymbol.GetPeripheral()` возвращает `False`. Этот getter относится к другим полям; не уничтожать готовый ГОСТ-символ слепым переустановлением ISO-флагов.
- `IsDangling=False` при нулевом количестве привязок означает свободную аннотацию, а не сохранённую связь с моделью.

## Официальные интерфейсы

- [SetLeaderAttachmentPointAtIndex](https://help.solidworks.com/2019/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IAnnotation~SetLeaderAttachmentPointAtIndex.html)
- [GetLeaderPointsAtIndex](https://help.solidworks.com/2022/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.iannotation~getleaderpointsatindex.html)
- [SetText](https://help.solidworks.com/2021/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IWeldSymbol~SetText.html)
- [GOST Weld Symbol Properties](https://help.solidworks.com/2024/english/Solidworks/sldworks/HIDD_WELD_GOST.htm)

Испытания и исходники: папка изделия ND2X4–6V, `04_Сопроводительная документация/Портирование_20261008`, `Проверка_привязки_нативной_сварки/Проверка_привязки.json` и `Исходники_автоматизации/apply_native_gost_support_welds.py`.
