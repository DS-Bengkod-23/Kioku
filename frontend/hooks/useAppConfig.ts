import { useQuery } from "@tanstack/react-query";
import { getAppConfig } from "@/lib/api";

// Setting dari .env (batas upload, interval polling, dll). Hampir tidak pernah berubah
// selama aplikasi jalan, jadi tidak perlu refetch sering. Selama data belum ada
// (`undefined`), pemanggil melewati pengecekan sisi FE — backend tetap memvalidasi.
export function useAppConfig() {
  return useQuery({
    queryKey: ["app-config"],
    queryFn: getAppConfig,
    staleTime: 5 * 60 * 1000,
  });
}
