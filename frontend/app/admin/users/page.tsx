"use client";

import React from "react";
import { toast } from "sonner";
import { Ban, CheckCircle2, KeyRound, Users } from "lucide-react";
import { cn, extractApiError } from "@/lib/utils";
import { useProfile } from "@/hooks/useProfile";
import {
    useAdminUsers,
    useSuspendUser,
    useUnsuspendUser,
    useUpdateUserRole,
    useResetUserPassword,
} from "@/hooks/useAdmin";
import type { UserAdminResponse, AppRole } from "@/types";

const ROLE_OPTIONS: AppRole[] = ["user", "admin", "superadmin"];

export default function AdminUsersPage() {
    const { data: me } = useProfile();
    const isSuperadmin = me?.role === "superadmin";

    const { data, isLoading, isError } = useAdminUsers();
    const users: UserAdminResponse[] = data?.items ?? data ?? [];

    const { mutate: suspendUser } = useSuspendUser();
    const { mutate: unsuspendUser } = useUnsuspendUser();
    const { mutate: updateRole } = useUpdateUserRole();
    const { mutate: resetPassword, isPending: isResetting } = useResetUserPassword();

    const handleToggleSuspend = (user: UserAdminResponse) => {
        const action = user.suspended_at ? unsuspendUser : suspendUser;
        action(user.id, {
            onSuccess: () =>
                toast.success(user.suspended_at ? "Akun diaktifkan kembali." : "Akun disuspend."),
            onError: (err) => toast.error(extractApiError(err, "Gagal memperbarui status akun.")),
        });
    };

    const handleRoleChange = (user: UserAdminResponse, role: AppRole) => {
        if (role === user.role) return;
        updateRole(
            { userId: user.id, role },
            {
                onSuccess: () => toast.success(`Role ${user.name} diubah jadi ${role}.`),
                onError: (err) => toast.error(extractApiError(err, "Gagal mengubah role.")),
            }
        );
    };

    const handleResetPassword = (user: UserAdminResponse) => {
        resetPassword(user.id, {
            onSuccess: () => toast.success(`Email reset password terkirim ke ${user.email}.`),
            onError: (err) => toast.error(extractApiError(err, "Gagal mengirim email reset password.")),
        });
    };

    return (
        <div className="max-w-6xl mx-auto px-6 py-8 space-y-6">
            <div>
                <h1 className="font-display text-xl font-bold text-slate-900 flex items-center gap-2.5">
                    <Users className="text-slate-700" size={20} /> Manajemen Pengguna
                </h1>
                <p className="text-slate-500 text-sm mt-1">Suspend akun, kelola role, dan reset password.</p>
            </div>

            <div className="bg-white border border-slate-200 shadow-sm rounded-2xl overflow-hidden">
                {isLoading ? (
                    <div className="p-8 space-y-2">
                        {[...Array(4)].map((_, i) => (
                            <div key={i} className="h-12 rounded-xl bg-slate-100 animate-pulse" />
                        ))}
                    </div>
                ) : isError ? (
                    <p className="text-center text-rose-400 py-10 text-sm">Gagal memuat daftar pengguna.</p>
                ) : users.length === 0 ? (
                    <p className="text-center text-slate-400 py-10 text-sm italic">Belum ada pengguna.</p>
                ) : (
                    <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                            <thead>
                                <tr className="border-b border-slate-200 text-left text-[11px] font-bold text-slate-500 uppercase tracking-wider">
                                    <th className="px-6 py-3">Nama</th>
                                    <th className="px-6 py-3">Email</th>
                                    <th className="px-6 py-3">Role</th>
                                    <th className="px-6 py-3">Status</th>
                                    <th className="px-6 py-3 text-right">Aksi</th>
                                </tr>
                            </thead>
                            <tbody>
                                {users.map((user) => (
                                    <tr key={user.id} className="border-b border-slate-100 last:border-0">
                                        <td className="px-6 py-3 font-semibold text-slate-900">{user.name}</td>
                                        <td className="px-6 py-3 text-slate-500">{user.email}</td>
                                        <td className="px-6 py-3">
                                            {isSuperadmin ? (
                                                <select
                                                    value={user.role}
                                                    onChange={(e) => handleRoleChange(user, e.target.value as AppRole)}
                                                    className="text-xs border border-slate-200 rounded-lg px-2 py-1.5 bg-white outline-none focus:border-indigo-400"
                                                >
                                                    {ROLE_OPTIONS.map((r) => (
                                                        <option key={r} value={r}>{r}</option>
                                                    ))}
                                                </select>
                                            ) : (
                                                <span className="text-xs font-bold uppercase tracking-wide text-slate-600">{user.role}</span>
                                            )}
                                        </td>
                                        <td className="px-6 py-3">
                                            <span
                                                className={cn(
                                                    "text-[10px] font-bold uppercase tracking-wide px-2 py-1 rounded-full",
                                                    user.suspended_at ? "bg-rose-50 text-rose-600" : "bg-emerald-50 text-emerald-700"
                                                )}
                                            >
                                                {user.suspended_at ? "Suspended" : "Aktif"}
                                            </span>
                                        </td>
                                        <td className="px-6 py-3">
                                            <div className="flex items-center justify-end gap-2">
                                                <button
                                                    onClick={() => handleToggleSuspend(user)}
                                                    title={user.suspended_at ? "Aktifkan kembali" : "Suspend akun"}
                                                    className={cn(
                                                        "p-1.5 rounded-lg border transition",
                                                        user.suspended_at
                                                            ? "border-emerald-200 text-emerald-600 hover:bg-emerald-50"
                                                            : "border-rose-200 text-rose-500 hover:bg-rose-50"
                                                    )}
                                                >
                                                    {user.suspended_at ? <CheckCircle2 size={14} /> : <Ban size={14} />}
                                                </button>
                                                {isSuperadmin && (
                                                    <button
                                                        onClick={() => handleResetPassword(user)}
                                                        disabled={isResetting}
                                                        title="Kirim email reset password"
                                                        className="p-1.5 rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50 transition disabled:opacity-50"
                                                    >
                                                        <KeyRound size={14} />
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>
        </div>
    );
}
