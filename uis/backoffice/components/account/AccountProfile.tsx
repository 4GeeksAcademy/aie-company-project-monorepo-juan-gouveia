"use client";

import ProfileForm from "@/components/account/ProfileForm";
import FormAlert from "@/components/auth/FormAlert";
import { useSession } from "@/hooks/useSession";
import type { Profile } from "@/types/auth";

// Datos de la cuenta: el email y el perfil vienen de GET /auth/me, que SessionProvider ya pidió al
// entrar en la zona protegida. Tras guardar, se actualiza la sesión y con ella el nombre de la cabecera.
export default function AccountProfile() {
  const { user, setUser } = useSession();
  if (!user) return null;

  function handleSaved(profile: Profile) {
    if (user) setUser({ ...user, profile });
  }

  return (
    <div className="flex flex-col gap-6">
      <section aria-labelledby="account-heading" className="rounded-lg border border-red-200 bg-white p-4 shadow-md md:p-6">
        <h2 id="account-heading" className="mb-3 text-lg font-semibold text-red-700">
          Cuenta
        </h2>
        <dl className="text-sm text-black">
          <dt className="font-semibold text-red-700">Email</dt>
          <dd className="break-all">{user.email}</dd>
        </dl>
      </section>

      <section aria-labelledby="profile-heading" className="rounded-lg border border-red-200 bg-white p-4 shadow-md md:p-6">
        <h2 id="profile-heading" className="mb-3 text-lg font-semibold text-red-700">
          Nombre y contacto
        </h2>
        {user.profile ? (
          // La key reinicia el formulario si la sesión pasa a otra cuenta (por ejemplo, desde otra pestaña).
          <ProfileForm key={user.profile.id} profile={user.profile} onSaved={handleSaved} />
        ) : (
          <FormAlert tone="info">Esta cuenta no tiene perfil. Contacta con un administrador.</FormAlert>
        )}
      </section>
    </div>
  );
}
