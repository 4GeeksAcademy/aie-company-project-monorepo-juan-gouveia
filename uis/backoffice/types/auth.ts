// Tipos de los dominios auth, users y profiles de la API de Brasaland (ticket AUTH-01).

export type Role = "admin" | "manager" | "user";

// Perfil tal como lo devuelve la API (`ProfileRead`): solo nombre y contacto, sin `id` ni `user_id`
// (docs/serialization-audit.md, 4.3).
export interface Profile {
  name: string | null;
  phone: string | null;
  address: string | null;
}

// Campos editables del perfil; en PUT /profiles/me solo cambian los enviados y null vacía el campo.
export type ProfileFields = Profile;

// Respuesta de POST /auth/login.
export interface Token {
  access_token: string;
  token_type: "bearer";
}

// Respuesta de POST /auth/change-password (AUTH-03): los tokens anteriores dejan de valer y este
// los sustituye.
export interface PasswordChanged extends Token {
  message: string;
}

// Respuesta de GET /auth/me.
export interface CurrentUser {
  id: string;
  email: string;
  role: Role;
  profile: Profile | null;
}

// Respuesta de POST /users: el id de la cuenta creada y una confirmación, sin reenviar el email
// (docs/serialization-audit.md, U1).
export interface RegisteredUser {
  id: string;
  message: string;
}

// Cuerpo de POST /users. No admite `role`: los registros nuevos siempre son `user`.
export interface RegisterInput extends Partial<ProfileFields> {
  email: string;
  password: string;
}
