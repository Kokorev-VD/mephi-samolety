# Каталог эндпоинтов REST API (v0.1)

- **Версия:** 0.1 (черновик — основа API-справочника DOC-08 Спринта 2)
- **Дата:** 24.10.2026
- **Составитель:** Минасов М.Р.
- **Источник:** вычитка 7 контроллеров `D:\IdeaProjects\mephi-12\backend\src\main\kotlin\ru\command\mephi12\controller\*.kt` + `SecurityConfig.kt`, `JwtFilter.kt`, `application.yaml`
- **Система:** «Платформа для изучения и практики курса по криптографии в МИФИ» (криптотренажёр mephi-12)

**Базовый путь:** `/api` — задан в `application.yaml` (`server.servlet.context-path: /api`), порт 8083. Константы `URLConstants` (`/v1`, `/v1/public`, `/v1/admin`) контроллерами не используются — версионирования в путях нет.

**Модель доступа** (SecurityConfig + JwtFilter): без аутентификации — только `/api/auth/**` (и формально `/public/**`, которого нет); всё остальное — роль `ROLE_USER` (заголовок `Authorization: Bearer <JWT>`). Отдельной проверки ADMIN ни для одного действующего эндпоинта нет (см. Замечания).

## Главная таблица эндпоинтов

| № | Метод | Полный путь | Роли/доступ | Краткое назначение | Контроллер#метод | Вход | Выход |
|---|---|---|---|---|---|---|---|
| 1 | POST | `/api/auth/registration` | все | Регистрация нового пользователя, сразу выдаёт JWT | `AuthController#register` | тело: `RegistrationRequest{email, password, name, surname}` (email — regex+4–120, пароль 8–255, `@Valid`) | `LoginResponse{accessJwt}` |
| 2 | POST | `/api/auth/login` | все | Логин по email/паролю | `AuthController#login` | тело: `LoginRequest{email, password}` (валидация НЕ включена — нет `@Valid`) | `LoginResponse{accessJwt}` |
| 3 | GET | `/api/users/me/tasks` | USER | «История задач» текущего пользователя; фактически возвращает ВСЕ ранцевые задачи из БД (deprecated-сервис) | `UserController#getMyTasks` | — | `List<BackpackProblemResponse>` |
| 4 | PUT | `/api/users/me/groups` | USER | Вступить в группу по названию | `UserController#updateMyGroup` | query: `group` (название) | пусто (200) |
| 5 | GET | `/api/users/groups` | USER | Список всех групп | `UserController#getGroups` | — | `List<UserGroupDto{id, name, users:List<UUID>}>` |
| 6 | POST | `/api/tasks/session` | USER | Создать сессию решения (набор задач) по конфигурации группы | `ProblemController#createProblemSession` | query: `configuration` (имя конфигурации) | `ProblemSessionDto{id, createdAt, state, userId, problems:List<ProblemDto>}` |
| 7 | PUT | `/api/tasks/submit` | USER | Отправить решение задачи сессии на проверку | `ProblemController#check` | query: `statementId` (UUID); тело: JSON решения (raw String; формат зависит от типа — `BackpackProblemSubmitRequest` или `ElGamalSolution`) | `ProblemSubmitResponse{problemId, isOk, problemType, errorMessage}` |
| 8 | GET | `/api/tasks/groups/configurations` | USER | Конфигурации наборов задач группы (с флагом enabled) | `ProblemController#getConfigurations` | query: `groupId` (UUID) | `List<ProblemConfigurationDto{id, name, tasks:List<String>, enabled}>` |
| 9 | GET | `/api/tasks/backpack/editorial` | USER | Редакционная (эталонная) ранцевая задача — быстрый вызов с типом в query | `BackpackProblemController#editorial(GET)` | query: `type` (enum `ProblemType`) | `BackpackProblemEditorialResponse` |
| 10 | POST | `/api/tasks/backpack/editorial` | USER | Редакционная ранцевая задача с полными параметрами | `BackpackProblemController#editorial(POST)` | тело: `BackpackProblemEditorialRequest{power?, type, message, lightBackpack, omega?}` | `BackpackProblemEditorialResponse` |
| 11 | GET | `/api/backdoor/editorial` | USER | Редакционная задача о бэкдоре в ранцевой КС | `BackdoorController#editorial` | **тело**: `BackpackBackdoorProblemEditorialRequest{power?, message}` (GET с @RequestBody!) | `BackpackBackdoorProblemEditorialResponse{power, spaceSize, message, lightBackpack, omega:String, hardBackpack, encodedMessage, module:String, reverseOmega}` |
| 12 | GET | `/api/tasks/eigamal/editorial` | USER | Демонстрационный пример Эль-Гамаля с пояснениями шагов | `EIGamalController#editorial` | query: `bitLength` (int, defaultValue = "10") | `ElGamalDemo` (все промежуточные значения + строки-вычисления) |
| 13 | GET | `/api/tasks/eigamal` | USER | Задание Эль-Гамаля для самостоятельного решения | `EIGamalController#getTask` | query: `bitLength` (int, defaultValue = "10") | `ElGamalTask{p, g, x, m}` |
| 14 | GET | `/api/moderator/tasks/session` | USER (не ADMIN!) | Все сессии всех пользователей (модерация) | `ModeratorController#getSessions` | — | `List<ProblemSessionDto>` |

Итого: 14 действующих эндпоинтов (2 без аутентификации, 12 — `ROLE_USER`), плюс 1 закомментированный (№ 15 ниже).

### Недоступные/закомментированные

| № | Метод | Полный путь | Статус | Что должен был делать |
|---|---|---|---|---|
| 15 | PUT | `/api/tasks/eigamal` | закомментирован в `EIGamalController` | Сдача решения Эль-Гамаля вне сессии (`submitTask`, параметры `id` + `BackpackProblemSubmitRequest`) |

## Замечания для DOC-08

**Нетипичности:**
1. **GET с @RequestBody**: № 11 `GET /api/backdoor/editorial` — параметры в теле JSON, а не в query. Многие HTTP-клиенты/прокси не поддерживают тело у GET — зафиксировать в справочнике и поднять вопрос о смене на POST.
2. **PUT с сырой строкой**: № 7 `PUT /api/tasks/submit` объявляет `@RequestBody body: String` — фактический формат тела зависит от типа задачи (`BackpackProblemSubmitRequest` / `ElGamalSolution`); в справочнике расписать обе схемы с дискриминацией по типу задачи.
3. **Закомментированный эндпоинт** № 15 — не включать в перечень доступных, но упомянуть как план.
4. **Модерация без ADMIN**: № 14 `/api/moderator/**` в `SecurityConfig` закрыт только `hasAnyRole("USER")` — любой студент видит все сессии. Проверка ADMIN есть лишь в `JwtFilter` для URI, содержащих `/v1/admin`, но ни один контроллер не мапит `/v1/admin`. Кроме того, JWT всегда выпускается с `admin=false` (`JwtHelper.generateAccessToken(user.id, false)`) — получить ADMIN-токен через API невозможно.
5. **Несоответствие префиксов ролей**: `USER_ROLE = "ROLE_USER"`, но `ADMIN_ROLE = "ADMIN"` (без `ROLE_`) — Spring-конвенция `hasRole`/`hasAnyRole` соблюдена только для USER.
6. **Пути `/public/**` и `/v1/*`**: матчер `permitAll` для `/public/**` в `SecurityConfig` не соответствует ни одному эндпоинту; константы `API_VERSION_1`/`API_PUBLIC`/`API_ADMIN` объявлены, но не используются. Публичный — только `/api/auth/**` (JwtFilter его пропускает через `shouldNotFilter`).
7. **«История» возвращает чужие данные**: № 3 `GET /api/users/me/tasks` → `HistoryService.findAll()` — все `BackpackProblem` из БД, фильтра по пользователю нет; сервис помечен `@Deprecated("Should be removed")`.
8. **Дефолтные значения параметров**: `bitLength` (№ 12, 13) — `defaultValue = "10"` в контроллере; дефолты интерфейса `ElGamalService` (64/32) недостижимы. В сессиях задач bitLength Эль-Гамаля жёстко = 5.
9. **Особенности валидации**: `@Valid` есть только на регистрации (№ 1); у логина (№ 2) аннотации в DTO не активируются. `surname` в регистрации принимается, но не сохраняется (`UserMapper` берёт только email и name). Ошибки валидации → 400 со списком полей (ExceptionResolver).
10. **Опечатки в путях**: `eigamal` вместо `elgamal` (№ 12–13, класс `EIGamalController`) — зафиксировать как есть; лог-строка в `BackdoorController` называет чужой путь `/tasks/eigamal/editorial`.
11. **Deprecated-контроллер**: `BackpackProblemController` (№ 9–10) помечен комментарием `// Deprecated`, но доступен.
12. **Формат поля type**: в DTO ранца `type` — русское описание (`ProblemType.description`, напр. «Задача о Ранцевой КС»), а в query № 9 — enum `ProblemType` (англ. константы). Проверка решения сверяет именно `description`.
13. **Ограничение типов в сессии**: квалификаторы существуют только у `Backpack` и `ElGamal`; BACKPACK_BACKDOOR/BACKPACK_CODE_* в сессию не попадают (`ProblemType.getQualifier()` бросает исключение).
14. **Пустые ответы**: № 4 возвращает пустое тело (Unit → 200 OK); № 3/5/8/14 — без пагинации.

**Что уточнить у владельцев доменов:**
- Кокорев В.Д.: планируются ли реальные `getSelfProfile`/`getUserProfile` (сейчас заглушки без возврата)? Будет ли валидация на логине? Судьба № 3 (deprecated-история)?
- Анохин Г.А.: формат тела № 7 для каждого типа задачи; поведение при повторной отправке; допустимость нескольких параметров `configuration`; планы на 20-минутный таймаут (вынести в конфиг?).
- Георгиев Д.Д.: баг в `BackpackProblemHandler.when` (для CODE_DEGREES вызывается супервозрастающий солвер) — задокументировать как есть или чинить? Статус deprecation № 9–10?
- Минасов М.Р.: замену GET+body (№ 11) на POST; семантика `omega`/`module` как строк с ведущими нулями.
- Портнов Л.М.: стабилизация значений `bitLength` по умолчанию; нужен ли № 15 (сдача Эль-Гамаля вне сессии)?
- Самбьюи А.Ж.: как управляются группы/конфигурации (CRUD-эндпоинтов нет); доступ к № 14 и № 8 (нет проверки, что groupId — своя группа).
