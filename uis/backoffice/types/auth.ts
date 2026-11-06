// Tipos de los dominios auth, users y profiles de la API de Brasaland (ticket AUTH-01).

export type Role = "admin" | "manager" | "user";

export interface Profile {
  id: string;
  user_id: string;
  name: string | null;
  phone: string | null;
  address: string | null;
}

// Campos editables del perfil; en PUT /profiles/me solo cambian los enviados y null vacía el campo.
export type ProfileFields = Pick<Profile, "name" | "phone" | "address">;

// Respuesta de POST /auth/login.
export interface Token {
  access_token: string;
  token_type: "bearer";
}

// Respuesta de GET /auth/me.
export interface CurrentUser {
  id: string;
  email: string;
  role: Role;
  profile: Profile | null;
}

// Respuesta de POST /users: el usuario creado y su perfil vinculado.
export interface RegisteredUser {
  id: string;
  email: string;
  is_active: boolean;
  role: Role;
  created_at: string;
  profile: Profile | null;
}

// Cuerpo de POST /users. No admite `role`: los registros nuevos siempre son `user`.
export interface RegisterInput extends Partial<ProfileFields> {
  email: string;
  password: string;
}
