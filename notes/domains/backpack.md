# Карточка домена: Ранцевые криптосистемы (супервозрастающая и на степенях)

Владелец: Георгиев Д.Д.
Ключевые классы: `BackpackProblemController`, `BackpackProblemSolverService` (интерфейс), `AbstractBackpackProblemSolverService`, `BackpackSuperIncreasingProblemSolverServiceImpl`, `BackpackDegreesProblemSolverServiceImpl`, `BackpackProblemHandler`, `BackpackProblemsCheckerServiceImpl`, `BackpackProblemDao`, `BackpackProblemMapper`, утилиты `ProblemUtils`/`RandomUtils`.

## Сущности БД

| Сущность | Назначение | Ключевые поля/связи |
|---|---|---|
| `BackpackProblem` (таблица `backpack_problem`) | Условие ранцевой задачи (устаревшая линия, отдельная от `Problem`) | `power: Int?`, `type: ProblemType`, `message: List<Boolean>` (конвертер `BooleanListConverter`), `lightBackpack: List<BigInteger>` (BigIntegerListConverter), `omega`, `hardBackpack`, `encodedMessage`, `decodedMessage`, `module`, `reverseOmega` (все `BigInteger?` с конвертерами), `state: ProblemState` (NEW), `errorDescription: String?` |

Управляется через `BackpackProblemDao`. Конечные списки хранятся конвертерами в текстовые колонки (`JsonArrayConverter`-семейство в `utils`).

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/tasks/backpack/editorial?type={ProblemType}` | Редакционная (эталонная) задача: тип в query, остальные параметры по умолчанию → `BackpackProblemEditorialResponse` |
| POST | `/api/tasks/backpack/editorial` | То же с полным телом `BackpackProblemEditorialRequest{power?, type, message, lightBackpack, omega?}` → `BackpackProblemEditorialResponse` |

Оба требуют `ROLE_USER`. Контроллер помечен комментарием `// Deprecated` (и TODO «replace logging with log interceptor»).

Кроме того, домен обслуживает сессии задач (домен «Сессии задач»): бин `BackpackProblemsCheckerServiceImpl` зарегистрирован с qualifier `"Backpack"` и вызывается из `ProblemDecorator` для `POST /api/tasks/session` и `PUT /api/tasks/submit`.

## Ключевые классы и их ответственность

- `BackpackProblemController` — два редакционных эндпоинта; логирует ответ как JSON (собственный `ObjectMapper` + JavaTimeModule в companion).
- `BackpackProblemSolverService` — контракт `solve(request): BackpackProblemEditorialResponse`.
- `AbstractBackpackProblemSolverService` — общий алгоритм ранцевой КС: выбор p (из запроса или случайное из первых 20 простых), генерация сообщения, лёгкий ранец → модуль (сумма + 1) → омега (взаимно простая с модулем) → тяжёлый ранец `(li*omega) mod module` → обратная омега → шифртекст; собственные реализации gcd/modInverse.
- `BackpackSuperIncreasingProblemSolverServiceImpl` (qualifier `BackpackProblemTypeQualifier.CODE_SUPER_INCREASING` = «Супервозрастающая») — `fixLightBackpack`: приведение лёгкого ранца к строго сверхвозрастающей последовательности нужной длины.
- `BackpackDegreesProblemSolverServiceImpl` (qualifier «Кодирование степеней») — `fixLightBackpack`: элементы лёгкого ранца = степени p^i.
- `BackpackProblemHandler` — `@Primary`-диспетчер по `request.type` (см. Замечания про дублирующуюся ветку when).
- `BackpackProblemsCheckerServiceImpl` (bean-qualifier `BACKPACK_QUALIFIER` = «Backpack») — генерация задачи для сессии (случайный тип из CODE_DEGREES/CODE_SUPER_INCREASING, сообщение длины 3–5 с ≥1/3 нулей, частично скрытый лёгкий ранец, случайная омега; сохранение в `backpack_problem`) и пошаговая проверка решения: совпадение типа, длины/битов сообщения, длин ранцев, сверхвозрастаемость, модуль > суммы лёгкого ранца, взаимная простота омеги, тяжёлый ранец, обратная омега, шифртекст, расшифровка жадным алгоритмом (`solveSuperIncreasingBackpack`), положительность элементов.
- `BackpackProblemMapper` — `entityToResponse`, `requestToEntity`, `modifyEntity`.
- `ProblemUtils`/`RandomUtils` — `generateRandomMessage(sizeFrom=8, sizeTo=16)` (минимум 1/3 нулей), `generateRandomPartOfLightBackpack` (дописывает случайные «прогалы» в начало/конец десятичной записи элементов), `generateRandomNumber`, `generateCoprime` (в utils).

## Сценарии использования

1. Студент открывает теорию — `GET /api/tasks/backpack/editorial?type=BACKPACK_CODE_SUPER_INCREASING` → сервер генерирует полный эталон: лёгкий ранец, омега, модуль, тяжёлый ранец, обратную омегу, шифртекст — и логирует ответ.
2. Преподаватель задаёт свои параметры — `POST /api/tasks/backpack/editorial` с телом `{power, type, message, lightBackpack, omega}`; при omega не взаимно простой с модулем — ошибка 4xx/5xx «Омега должна быть взаимно простой с модулем».
3. Студент решает задачу из сессии: `PUT /api/tasks/submit?statementId=…` с телом `BackpackProblemSubmitRequest{power, type, message, lightBackpack, omega, hardBackpack, encodedMessage, decodedMessage, module, reverseOmega}` → по 11 пунктам проверки; любое несовпадение — `TaskSolverProblemException` с текстом, какой именно параметр неверен.
4. Генерация в сессии: часть элементов лёгкого ранца скрывается нулями (0–2 остаются), omega может отсутствовать — студент восстанавливает недостающее.

## Связи с другими доменами

- Опирается на: «Аутентификация» (JWT-доступ), «Сессии задач» (встраивается как checker по qualifier «Backpack»; тип задачи в `Problem` — BACKPACK).
- Предоставляет: генерацию/проверку ранцевых задач (супервозрастающая, на степенях), сущность-историю `BackpackProblem` (её же читает устаревший `GET /api/users/me/tasks`).
- Не связано с `BACKPACK_BACKDOOR` — тот живёт в отдельном домене «Бэкдор в ранцевой КС».

## Замечания для документирования

- В `BackpackProblemHandler.solve` ветка `ProblemType.BACKPACK_CODE_DEGREES -> superIncreasingSolver.solve(request)` повторяется второй раз (`when` с двумя одинаковыми условиями): для CODE_DEGREES фактически вызывается **супервозрастающий** солвер, ветка с `codeDegreesSolver` недостижима. Вопрос владельцу: это баг или задумано.
- В `checkCodeDegrees` проверка расшифрованного сообщения отсутствует (TODO в коде: «без информации о количестве и позиции дополнённых цифр невозможно однозначно декодировать») — в справочнике описать список реально проверяемых полей для этого типа.
- `fixLightBackpack` в чекере (для CODE_DEGREES) сравнивает элементы ранца со строковым представлением p^i.
- `BackpackProblem.type` в БД — это ProblemType, а в DTO `BackpackProblemResponse.type`/`SubmitRequest.type` — русское `description` («Задача о Ранцевой КС» и т.п.); проверка типа идёт по `task.type.description != response.type` — отразить в формате ответа.
- Контроллер объявлен устаревшим (`// Deprecated`), но остаётся в API; поле `state` в `BackpackProblemResponse` — строка.
- Часть кода генерации дублирует математику домена Эль-Гамаля (локальные gcd/modInverse вместо `ModularArithmetic`) — при документировании не смешивать.
