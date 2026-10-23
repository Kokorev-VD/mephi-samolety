# Карточка домена: Криптосистема Эль-Гамаля и математическая библиотека

Владелец: Портнов Л.М.
Ключевые классы: `EIGamalController`, `ElGamalService`/`ElGamalServiceImpl`, `ElGamalUtils`, `ElGamalModels` (ElGamalTask/ElGamalSolution/ElGamalDemo/ElGamalVerificationResult), `CryptoRandom`, `PrimeNumbers`, `ModularArithmetic`, `GroupTheory`, исключения `ElGamalException`-семейства.

## Сущности БД

Не имеет собственных сущностей — задачи Эль-Гамаля хранятся только внутри сессий как `Problem` (statement = JSON `ElGamalTask`) в домене «Сессии задач».

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/tasks/eigamal/editorial?bitLength=10` | Демонстрационный пример с пошаговыми пояснениями → `ElGamalDemo` |
| GET | `/api/tasks/eigamal?bitLength=10` | Задание для самостоятельного решения → `ElGamalTask{p, g, x, m}` |

Оба требуют `ROLE_USER`; `bitLength` — query-параметр с defaultValue `"10"` (дефолты интерфейса 64/32 к контроллеру не применяются).

В домене «Сессии задач» домен участвует как checker: бин `ElGamalServiceImpl` зарегистрирован с qualifier `"ElGamal"` и вызывается из `ProblemDecorator` (`generateProblem()` → `generateTask(5)`, `check()` → `verifySolution`). Отдельный эндпоинт сдачи решения `PUT /tasks/eigamal` (submitTask) **закомментирован** в контроллере.

## Ключевые классы и их ответственность

- `EIGamalController` — два GET-эндпоинта с логированием ответа; имя класса с опечаткой (EIGamal).
- `ElGamalService` — контракт: generateDemo(bitLength=64, message?), generateTask(bitLength=32), checkSolution, encrypt, decrypt.
- `ElGamalServiceImpl` — реализация, полностью делегирует `ElGamalUtils`; дополнительно реализует `ProblemsCheckerService<ElGamalTask>` для сессий: `check` десериализует statement/решение и возвращает `ProblemSubmitResponse{isOk, errorMessage}`; `generateProblem() = generateTask(5)`.
- `ElGamalUtils` (object) — ключевые пары (p, g, x, y=g^x mod p), шифрование (c1=g^k, c2=m*y^k), расшифрование (s=c1^x, m=c2*s^-1), `createDemoExample` (со строками-пояснениями вида `"g^x mod p = y"`), `generateTask` (учебные числа), `verifySolution` — поэтапная проверка y, c1, c2, расшифровки и совпадения с исходным m (каждый шаг даёт конкретное сообщение об ошибке), `solveDemoTask`.
- `CryptoRandom` — `SecureRandom`: randomBigInteger(min,max), randomBigInteger(bitLength), randomCoprime(n).
- `PrimeNumbers` — generatePrime (BigInteger.probablePrime), isProbablePrime(certainty=100), generateSafePrime (p где (p-1)/2 тоже простое).
- `ModularArithmetic` — modPow, modMultiply, modInverse (null при отсутствии), gcd, extendedGcd (расширенный Евклид, Triple(gcd,s,t)).
- `GroupTheory` — поиск порождающего Z_p*: для p < 32 бит — полный перебор элементов, иначе вероятностная проверка (Fermat + safe prime 2q+1, до 50 попыток, fallback 2 или 3); собственный инфиксный `until` для BigInteger.
- `ElGamalModels` — DTO предметной области: `ElGamalTask{p,g,x,m}`, `ElGamalSolution{y,k,c1,c2,decryptedMessage}`, `ElGamalDemo` (все промежуточные значения + строки вычислений), `ElGamalVerificationResult{isCorrect, errorMessage}`.
- Исключения: `ElGamalParameterException`, `ElGamalEncryptionException`, `ElGamalDecryptionException` (наследники `ElGamalException`) — маппятся в JSON общим `ExceptionResolver`.

## Сценарии использования

1. Студент открывает теорию: `GET /api/tasks/eigamal/editorial` → полный демо-пример: p, g, x, m, y, k, c1, c2, y^k, s, s^-1, расшифрованное сообщение и текстовые пояснения каждого шага — готовый материал для методички.
2. Студент тренируется: `GET /api/tasks/eigamal?bitLength=10` → `ElGamalTask{p, g, x, m}`; решает вручную (найти y, выбрать k, вычислить c1, c2, расшифровать).
3. Студент сдаёт решение в рамках сессии: `PUT /api/tasks/submit?statementId=…` с телом `ElGamalSolution` → `verifySolution` по шагам; первая же ошибка возвращает `isOk=false` и сообщение вида «Некорректное значение c1. Должно быть …».
4. Генерация в сессии (`POST /api/tasks/session`) — задачи Эль-Гамаля создаются фиксированно с bitLength=5.

## Связи с другими доменами

- Опирается на: «Аутентификация» (JWT-доступ).
- Предоставляет: checker `"ElGamal"` домену «Сессии задач» (через `Map<String, ProblemsCheckerService<*>>` в `ProblemDecorator`); mathLibrary (`CryptoRandom`, `PrimeNumbers`, `ModularArithmetic`) — потенциально общий математический фундамент, фактически остальными доменами не используется (ранец и бэкдор держат собственные реализации gcd/modInverse).
- Проблема Эль-Гамаля не персистится отдельно — только statement-JSON в `Problem`.

## Замечания для документирования

- Имя пути — `/api/tasks/eigamal` (с опечаткой `eigamal` вместо `elgamal`) — зафиксировать как есть, переименование сломает клиентов.
- `bitLength` в обоих эндпоинтах имеет defaultValue `"10"`; дефолты интерфейса (64/32) недостижимы через контроллер.
- Закомментированный эндпоинт `PUT /tasks/eigamal` (submitTask) — в каталог включать с пометкой «недоступен».
- В `verifySolution` решение считается верным при корректности всех промежуточных значений; повторная сдача решённой задачи не блокируется (в отличие от ранца, где есть «Задача уже решена!»).
- `x` (секретный ключ) передаётся студенту в `ElGamalTask` — это учебная задача, но в описании API стоит подчеркнуть, что «секретность» условная.
- В `GroupTheory.findGenerator` для больших p используется эвристика — для больших bitLength генератор может быть найден неточно; методические примеры рассчитаны на маленькие bitLength.
- `ElGamalServiceImpl.generateProblem` жёстко кодирует bitLength=5 — параметры генерации в сессии не настраиваются конфигурацией.
