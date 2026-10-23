# Карточка домена: Аутентификация и пользователи

Владелец: Кокорев В.Д.
Ключевые классы: `AuthController`, `UserController`, `AuthService`/`AuthServiceImpl`, `JwtHelper`, `JwtFilter`, `JwtParser`, `SecurityConfig`, `UserService`/`UserServiceImpl`, `UserGroupService`/`UserGroupServiceImpl`, `UserPrincipal`, `Authority`, `Roles.kt`, `UserMapper`, `AuthUtils.kt`.

## Сущности БД

| Сущность | Назначение | Ключевые поля/связи |
|---|---|---|
| `User` (таблица `` `User` ``) | Учётная запись пользователя | `email` (unique, NOT NULL), `name`, `hash` (BCrypt-хеш пароля), `group` → `UserGroup` (ManyToOne, EAGER), `problemSessions` → `ProblemSession` (OneToMany, orphanRemoval) |
| `UserGroup` (таблица `user_group`) | Учебная группа пользователей | `name`, `users` → `User` (OneToMany, CASCADE ALL), `problemConfigs` → `UserGroupProblemConfiguration` (OneToMany, CASCADE ALL, orphanRemoval) |
| `AbstractEntity` (`@MappedSuperclass`) | Базовый класс всех сущностей | `id: UUID` (генерируется БД), `createdAt: LocalDateTime` (`@CreationTimestamp`) |

Наследует общий каркас от `AbstractEntity` (id, created_at).

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| POST | `/api/auth/registration` | Регистрация: `@Valid RegistrationRequest{email, password, name, surname}` → `LoginResponse{accessJwt}` |
| POST | `/api/auth/login` | Логин: `LoginRequest{email, password}` → `LoginResponse{accessJwt}` |
| GET | `/api/users/me/tasks` | «История» задач текущего пользователя (реально возвращает все `BackpackProblem` из БД — см. Замечания) |
| PUT | `/api/users/me/groups?group={name}` | Привязка текущего пользователя к группе по названию |
| GET | `/api/users/groups` | Список всех групп (`List<UserGroupDto>`) |

Доступ: `/api/auth/**` — без аутентификации (permitAll + `JwtFilter.shouldNotFilter`); остальные — роль `ROLE_USER`.

## Ключевые классы и их ответственность

- `AuthController` — registration/login, выдача JWT; на registration включена валидация `@Valid`, на login — нет.
- `AuthServiceImpl` — регистрация (создание пользователя через `UserService`, кодирование пароля BCrypt) и логин (сверка пароля `encoder.matches`); оба метода выдают токен через `JwtHelper.generateAccessToken(user.id, false)`.
- `JwtHelper` — сборка access-токена: claims `userId`, `permissions` (пустой список), `authorities`; срок жизни `spring.security.jwt.access.lifetime` в днях (`ChronoUnit.DAYS`).
- `JwtParser` — HMAC-SHA256 (jjwt 0.11.5, `SignatureAlgorithm.HS256`), ключ из `spring.security.jwt.secret`; парсинг заголовка `Authorization: Bearer …`, извлечение `userId` и `authorities` в `UserPrincipal`; отдельные ошибки для истёкшего токена («Авторизуйтесь заново», 401).
- `JwtFilter` (`OncePerRequestFilter`) — вставлен перед `UsernamePasswordAuthenticationFilter`; пропускает запросы с путями `/public` и `/auth`; кладёт `UserPrincipal` в `SecurityContextHolder`; для URI, содержащих `/v1/admin`, требует authority `ADMIN`.
- `SecurityConfig` — CSRF off, CORS через `AppConfig.corsFilter`, сессии STATELESS, матчеры: `/public/**` и `/auth/**` → permitAll, `/**` → `hasAnyRole("USER")`; BCryptPasswordEncoder.
- `UserService`/`UserServiceImpl` — CRUD пользователя, поиск по email/id, `setMyGroup` (привязка группы), `getCurrentProblemSession` (активная сессия NEW), `createUser` (проверка дубля email, хеширование пароля). `getSelfProfile`/`getUserProfile` — заглушки с закомментированным возвратом.
- `UserGroupService`/`UserGroupServiceImpl` — поиск группы по имени, сохранение, `findAll` → `UserGroupDto{id, name, users}`.
- `UserMapper` — `RegistrationRequest` → `User` (берёт только `email` и `name`; `surname` игнорируется; пароль хешируется отдельно в сервисе).
- `UserPrincipal` — `AbstractAuthenticationToken` с `userId: UUID` и authorities.
- `Authority`/`Roles.kt` — enum `USER`→`ROLE_USER`, `ADMIN`→`ADMIN`; константы `USER_ROLE`, `ADMIN_ROLE`.
- `AuthUtils.kt` — `getPrincipal(): UUID` и `getAuthorities()` из `SecurityContextHolder` (используются всеми доменами).

## Сценарии использования

1. Студент регистрируется (`POST /api/auth/registration`, валидируются email по `EMAIL_REGEX`, длина email 4–120, пароль 8–255) → пользователь с BCrypt-хешем сохраняется в БД → сразу выдаётся JWT.
2. Студент логинится (`POST /api/auth/login`) → сверка пароля с хешем → `LoginResponse{accessJwt}`; неверный пароль → 401 «Неправильный пароль».
3. Любой запрос с заголовком `Authorization: Bearer <jwt>` проходит `JwtFilter` → `UserPrincipal` доступен сервисам (`getPrincipal()`); без заголовка → 401 «Вы неавторизованы».
4. Студент вступает в группу (`PUT /api/users/me/groups?group=УчебнаяГруппа`) → далее домену сессий задач доступна конфигурация этой группы.

## Связи с другими доменами

- Опирается на: «Конфигурации и модерация» (сущность `UserGroup`, связка с `ProblemConfiguration`).
- Предоставляет: `getPrincipal()`/авторизацию всем доменам; `User.group` — домену «Сессии задач» (без группы сессию не создать); `User` — владельцу сессий (`ProblemSession.user`).

## Замечания для документирования

- **ADMIN-токен получить нельзя**: `generateAccessToken(user.id, false)` вызывается всегда с `admin=false` — роли ADMIN через API никто не получает. Роль задекларирована, но не выдаётся.
- `ADMIN_ROLE = "ADMIN"` без префикса `ROLE_` (у USER — `ROLE_USER`) — отступление от конвенции Spring Security `hasRole/hasAnyRole`.
- Константы `URLConstants` (`/v1/public`, `/v1/admin`) не используются ни одним контроллером; матчер `/public/**` в `SecurityConfig` тоже не соответствует ничему. Не путать в документации: реальных публичных путей только `/api/auth/**`.
- `GET /api/users/me/tasks` возвращает `HistoryService.findAll()` — **все** задачи `BackpackProblem` из БД, а не только задачи текущего пользователя; сам `HistoryServiceImpl` помечен `@Deprecated("Should be removed")`.
- У `login` нет `@Valid` — аннотации валидации в `LoginRequest` фактически не применяются; у `registration` — применяются.
- `RegistrationRequest.surname` принимается, но теряется (не сохраняется в `User`).
- `UserMapper` помечен TODO «пароль в маппере» — хеширование сейчас в `UserServiceImpl`.
- Секрет и время жизни токена — только из окружения: `JWT_SECRET`, `ACCESS_TOKEN_LIFETIME` (в днях); при отсутствии секрета `JwtParser` падает с NPE при первом использовании.
