const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

interface Options {
  token?: string | null;
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  /** Só para chamadas feitas no servidor (Server Components). */
  revalidate?: number;
}

export async function api<T>(path: string, opts: Options = {}): Promise<T> {
  const headers: Record<string, string> = {};
  if (opts.body !== undefined) headers["Content-Type"] = "application/json";
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`;

  let res: Response;
  try {
    res = await fetch(`${BASE_URL}${path}`, {
      method: opts.method ?? "GET",
      headers,
      body: opts.body !== undefined ? JSON.stringify(opts.body) : undefined,
      signal: opts.signal,
      ...(opts.revalidate !== undefined ? { next: { revalidate: opts.revalidate } } : {}),
    });
  } catch {
    throw new ApiError(0, "Não foi possível conectar ao servidor.");
  }

  if (!res.ok) {
    // Erros da API: {"erro": {"status", "mensagem", "detalhes"}}
    let mensagem = "Algo deu errado. Tente novamente.";
    try {
      const data = await res.json();
      if (data?.erro?.mensagem) mensagem = data.erro.mensagem;
    } catch {
      // corpo não é JSON
    }
    throw new ApiError(res.status, mensagem);
  }

  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}
