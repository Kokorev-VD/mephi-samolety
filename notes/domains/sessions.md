# Карточка домена: Сессии задач

Владелец: Анохин Г.А.
Ключевые классы: `ProblemController`, `ProblemDecorator`, `ProblemsCheckerService` (интерфейс), `ProblemAutoFailScheduler`, `ProblemDao`, `ProblemSessionDao`, DTO `ProblemSessionDto`/`ProblemDto`/`ProblemSubmitResponse`.

## Сущности БД

| Сущность | Назначение | Ключевые поля/связи |
|---|---|---|
| `ProblemSession` (таблица `problem_session`) | Набор задач («сессия решения») одного пользователя | `sessionState: ProblemState` (NEW/SOLVED/FAILED, по умолчанию NEW), `user` → `User` (ManyToOne, EAGER), `problems` → `Problem` (OneToMany, CASCADE ALL, EAGER); `toDto()` → `ProblemSessionDto` |
| `Problem` (таблица `problem`) | Отдельная задача внутри сессии | `statement: String` (`@Lob`, JSON-сериализация условия), `type: ProblemType`, `state: ProblemState` (NEW/SOLVED/FAILED), `problemSession` → `ProblemSession` (ManyToOne, EAGER); `toDto()` → `ProblemDto` |

Перечисления: `ProblemState` — NEW «Задание решается» / SOLVED «Задание верно решено» / FAILED «Задание решено неверно»; `ProblemType` — BACKPACK_CODE_SUPER_INCREASING, BACKPACK_CODE_DEGREES, BACKPACK, BACKPACK_BACKDOOR, EL_GAMAL.

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/tasks/session?configuration={name}` | Создать сессию решения по конфигурации группы → `ProblemSessionDto` |
| PUT | `/api/tasks/submit?statementId={UUID}` + тело (JSON решения) | Проверить решение задачи → `ProblemSubmitResponse{problemId, isOk, problemType, errorMessage}` |

Оба требуют `ROLE_USER`. Через `ModeratorController` (домен «Конфигурации и модерация») доступен просмотр всех сессий: `GET /api/moderator/tasks/session`.

## Ключевые классы и их ответственность

- `ProblemController` — два пользовательских эндпоинта + логирование входящих запросов (`log.info`).
- `ProblemDecorator` — оркестратор: находит разрешённые конфигурации группы пользователя (`GroupConfigService.enabledConfigs`), создаёт `ProblemSession`, для каждого квалификатора из `taskServices` берёт из `Map<String, ProblemsCheckerService<*>>` бин-генератор (по bean-qualifier «Backpack»/«ElGamal»), сериализует условие в JSON и сохраняет `Problem`; `check()` — проверка владельца, состояния, делегирование checker'у, переходы состояний задачи и сессии; `getSessions()` — все сессии (для модератора).
- `ProblemsCheckerService<PROBLEM_RESPONSE>` — контракт генерации/проверки: `generateProblem(): PROBLEM_RESPONSE`, `check(statement: String, solutionRequest: String): ProblemSubmitResponse` (обе строки — JSON).
- `ProblemAutoFailScheduler` — `@Scheduled(fixedRate = 60_000)` (60 с), `@Transactional`: 1) нативный `UPDATE problem SET state='FAILED' WHERE state='NEW' AND created_at < now() - INTERVAL '20 MINUTES'`; 2) перебор всех сессий: если задач в NEW не осталось, а сессия NEW → помечается SOLVED. В коде комментарий «неэффективно» (полный `findAll()` сессий с EAGER-связями).
- `ProblemDao` / `ProblemSessionDao` — Spring Data-репозитории; `ProblemDao.expireProblems()` — модифицирующий нативный запрос истечения.

## Сценарии использования

1. Студент с группой создаёт сессию: `POST /api/tasks/session?configuration=Sem4` → если уже есть активная сессия (NEW) — ошибка «Вы уже решаете набор задач!»; иначе по цепочке `taskServices` конфигурации генерируются задачи (Backpack/ElGamal), сессия сохраняется со статусом NEW → `ProblemSessionDto` со списком `ProblemDto{id, statement(JSON), type, state, sessionId}`.
2. Студент отправляет решение: `PUT /api/tasks/submit?statementId=UUID` (тело — JSON решения) → проверки: задача существует; владелец — текущий пользователь («Вы не решаете набор задач…»); сессия в NEW → checker по типу задачи → `isOk=true` → `Problem.state=SOLVED`, иначе `FAILED`; когда все задачи сессии закрыты — сессия SOLVED (все решены) или FAILED (есть провал).
3. Автопровал: задача в NEW висит более 20 минут → планировщик каждые 60 с переводит её в FAILED и закрывает сессию — студент не может решать бесконечно.
4. Без группы сессию создать нельзя — «У вас нет группы!» (ResourceNotFoundException из `ProblemDecorator.getAllAllowedSessionConfigs`).

## Связи с другими доменами

- Опирается на: «Аутентификация» (`getPrincipal()`, `User.group`, `UserService.getCurrentProblemSession`), «Конфигурации и модерация» (`GroupConfigService`, `ProblemConfiguration.taskServices`), «Ранцевые КС» и «Эль-Гамаль» (генерация и проверка задач по квалификаторам).
- Предоставляет: жизненный цикл задач и сессий, формат `ProblemSubmitResponse`; модератору — `getSessions()`.
- Тип BACKPACK_BACKDOOR в сессии не участвует: `ProblemType.getQualifier()`/`getByQualifier()` поддерживают только `Backpack` и `ElGamal`.

## Замечания для документирования

- `PUT /api/tasks/submit` принимает тело как сырую строку (`@RequestBody body: String`) — разбор JSON происходит внутри checker'ов.
- Правила доступа к задаче проверяются в `ProblemDecorator.check` вручную (не в Spring Security): принадлежность по `problemSession.user.id == getPrincipal()`.
- Пере-отправка решённой задачи: checker'ы ранца бросают «Задача уже решена!» (TaskSolverProblemException), у Эль-Гамаля такой проверки нет.
- `ProblemType` содержит 5 значений, но квалификаторы есть только у BACKPACK (=`"Backpack"`) и EL_GAMAL (=`"ElGamal"`); для остальных `getQualifier()` бросает исключение — в API-справочнике это ограничение стоит отразить.
- `generateProblem()` Эль-Гамаля в сессии всегда использует bitLength=5 (`ElGamalServiceImpl.generateProblem`), независимо от параметров редакционных эндпоинтов.
- Истечение задач зашито в SQL (20 минут) и не вынесено в конфигурацию.
