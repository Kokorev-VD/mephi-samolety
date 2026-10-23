# Карточка домена: Конфигурации задач, модерация, модель данных и инфраструктура

Владелец: Самбьюи А.Ж.
Ключевые классы: `ModeratorController`, `GroupConfigService`, `ProblemConfiguration`, `UserGroupProblemConfiguration`, `UserGroup`, `ProblemConfigurationDao`, `UserGroupDao`, `ProblemConfigurationDto`, `Mephi12Application`, `AppConfig`, `ObjectMapperConfig`, `ExceptionResolver`, `docker-compose.yaml`, `Dockerfile`, `application.yaml`, `build.gradle.kts`.

## Сущности БД (модель данных, 8 сущностей)

| Сущность | Назначение | Ключевые поля/связи |
|---|---|---|
| `AbstractEntity` | @MappedSuperclass — общий каркас | `id: UUID`, `createdAt: LocalDateTime` |
| `User` (`` `User` ``) | Учётная запись | `email` (unique), `name`, `hash` (BCrypt), `group` → UserGroup, `problemSessions` OneToMany |
| `UserGroup` (`user_group`) | Учебная группа | `name`, `users` OneToMany (CASCADE ALL), `problemConfigs` → UserGroupProblemConfiguration (CASCADE ALL, orphanRemoval) |
| `UserGroupProblemConfiguration` (`user_group_problem_configuration`) | Связка «группа ↔ конфигурация» с переключателем | `group` ManyToOne (LAZY), `problemConfiguration` ManyToOne (LAZY), `enabled: Boolean = true` |
| `ProblemConfiguration` (`problem_configuration`) | Именованный набор типов задач | `name`, `taskServices: List<String>` (@ElementCollection, таблица `problem_configuration_task_services` — квалификаторы «Backpack»/«ElGamal»), `groupLinks` OneToMany |
| `ProblemSession` (`problem_session`) | Сессия решения (набор задач) | `sessionState`, `user` → User, `problems` → Problem |
| `Problem` (`problem`) | Задача сессии | `statement` (@Lob JSON), `type`, `state`, `problemSession` → ProblemSession |
| `BackpackProblem` (`backpack_problem`) | Условие ранцевой задачи (устаревшая линия + история) | power, type, message, lightBackpack, omega, hardBackpack, encodedMessage, decodedMessage, module, reverseOmega, state, errorDescription |

Схема БД создаётся Hibernate `ddl-auto: update` — миграций (Flyway/Liquibase) нет.

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/api/moderator/tasks/session` | Список всех сессий всех пользователей (`List<ProblemSessionDto>`) — «модерация» |

Собственный эндпоинт один; при этом по данным конфигураций работает чужой эндпоинт `GET /api/tasks/groups/configurations?groupId={UUID}` (`ProblemController` → `GroupConfigService.getConfigs`) и создаётся `POST /api/tasks/session?configuration=`. Существенных деталей: в `SecurityConfig` путь `/api/moderator/**` защищён только требованием роли USER (как и всё `/**`), отдельного требования ADMIN нет (см. Замечания).

## Ключевые классы и их ответственность

- `ModeratorController` — просмотр всех сессий через `ProblemDecorator.getSessions()`.
- `GroupConfigService` — `getConfigs(groupId)`: все конфигурации группы c флагом `enabled` (`ProblemConfigurationDto{id, name, tasks, enabled}`); `enabledConfigs(groupId)`: только включённые (используются при создании сессии).
- `Mephi12Application` — `@SpringBootApplication`, `@EnableScheduling`; при локальном запуске подгружает `.env` через dotenv-java (2.2.0).
- `AppConfig` — CORS-фильтр: `allowCredentials=true`, все origin-паттерны (`*`), все заголовки и методы.
- `ObjectMapperConfig` — общий ObjectMapper с KotlinModule и JavaTimeModule.
- `ExceptionResolver` — @RestControllerAdvice: любая ошибка → JSON-представление `AppException` (status, message, timestamp); `MethodArgumentNotValidException` → 400 со списком полей.
- Инфраструктура: `build.gradle.kts` — Kotlin 1.9.25, Spring Boot 3.4.0, Java 17, стартеры Web/JPA/Security/Validation/Actuator, jjwt 0.11.5, postgresql-драйвер, dotenv-java.

## Сценарии использования

1. Преподаватель настраивает группе «Sem4» конфигурацию `["Backpack", "ElGamal", "ElGamal"]` и включает её (`enabled=true`) — у студентов группы при `POST /api/tasks/session?configuration=Sem4` генерируются ровно эти задачи; `enabled=false` скрывает конфигурацию (создание сессии по ней упадёт с «Problem configuration not found»).
2. Пользователь смотрит доступные наборы: `GET /api/tasks/groups/configurations?groupId=…` → список с флагами.
3. Модератор просматривает прогресс: `GET /api/moderator/tasks/session` → все сессии с задачами и состояниями (без пагинации).
4. Развёртывание: `docker-compose up` → поднимается `mephi12-db` (postgres:17-alpine, БД `mephi12`, порт 5432, healthcheck `pg_isready -U mephi12`, volume `mephi12-data`) и после его готовности `mephi12-core` (сборка gradle:8.13.0-jdk17 → openjdk:17, порт 8083, env из `.env`).

## Связи с другими доменами

- Опирается на: «Сессии задач» (читает `ProblemSession` через `ProblemDecorator`), «Аутентификация» (`User`, `UserGroup`, роли).
- Предоставляет: `GroupConfigService` и сущности конфигураций домену «Сессии задач»; инфраструктуру (context-path `/api`, порт 8083, переменные окружения, CORS, обработку ошибок) — всем доменам; единую модель данных (8 сущностей) для DOC по БД.

## Замечания для документирования

- **Доступ модератора**: `GET /api/moderator/tasks/session` фактически доступен любому аутентифицированному USER — требование ADMIN в `SecurityConfig` не настроено, а проверка ADMIN в `JwtFilter` срабатывает только для путей с `/v1/admin` (таких эндпоинтов нет). Плюс ADMIN-токен сейчас вообще не выдаётся. Отметить в DOC-08 и в модели угроз.
- `URLConstants`: `/v1/public`, `/v1/admin` объявлены, но не используются контроллерами; версионирования API нет (базовый путь — просто `/api` из `server.servlet.context-path`).
- application.yaml: `spring.application.name = task-tracker` (не совпадает с названием проекта), порт 8083, `show-sql: true`, `ddl-auto: update` — для production задокументировать риск.
- Переменные окружения (обязательные): `JWT_SECRET`, `ACCESS_TOKEN_LIFETIME` (дни), `DATABASE_URL`, `DATABASE_USER`, `DATABASE_PASSWORD`; в docker-compose переменные БД дублируются (POSTGRES_USER/PASSWORD, БД `mephi12`).
- `GET /api/tasks/groups/configurations` доступен с любым groupId — можно перечислить конфигурации чужой группы (проверки прав нет).
- `dao.findById(groupId).orElseThrow()` в `GroupConfigService` без сообщения — падает с пустой 500-й ошибкой.
- Удаление/создание конфигураций и групп API не покрывает — только чтение и переключение `enabled` на уровне БД; эндпоинтов для CRUD конфигураций нет (вопрос на Спринт 2: как преподаватель управляет наборами).
- Actuator в зависимостях подключен, в application.yaml не настроен (эндпоинты по умолчанию).
