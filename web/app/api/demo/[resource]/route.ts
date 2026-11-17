import { proxyDemo } from "../../../../lib/proxy";
export const dynamic = "force-dynamic";
export const runtime = "nodejs";
type Context = { params: Promise<{ resource: string }> };
async function handler(request: Request, context: Context) {
  return proxyDemo(request, (await context.params).resource, {
    baseURL: process.env.API_BASE_URL,
    origin: process.env.APP_ORIGIN,
    key: process.env.PROXY_KEY,
  });
}
export const GET = handler;
export const POST = handler;
export const PUT = handler;
export const DELETE = handler;
