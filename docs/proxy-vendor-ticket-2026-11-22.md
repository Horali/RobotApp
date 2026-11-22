# Proxy ticket — us-ps-2-newyork refuses the platforms from the phone's tunnel

Written 2026-11-22 17:20 WIB after a measured login attempt. This is the material for the vendor (or
for whoever owns the proxy account). One proxy works, one does not, on the same phone, the same app,
minutes apart.

## The two exits

| proxy | label | exit | result on the phone |
|---|---|---|---|
| `7d8a1a48-e530-474b-8ba3-632dbf879ff9` | us-ps-1-virginia | 208.214.162.185 | **works** |
| `dbe4201d-8721-48e2-8488-e1c09ab59f3a` | us-ps-2-newyork | 65.195.107.138 | **refuses platform TCP** |

Both brands (Speed `a271b3cb…`, Timmy `42637bcb…`) point at **newyork**; the throwaway
(`a3fbbea9…`) points at **virginia**.

## What was measured (2026-11-22, all on the phone)

1. **16:58** — `robot leak --user 10` (Speed's space): VPN up, always-on + lockdown, but
   `could not read the trace page`. The screenshot of that check is `1.1.1.1/cdn-cgi/trace` →
   **ERR_CONNECTION_REFUSED**.
2. **17:05** — one TikTok login attempt for Speed (`login-speed-tt6`), with the working email and the
   vault intact. The flow reached the login screen, typed `horalixscripts3@gmail.com`, tapped Continue:
   the button **spins forever** and the flow times out after 30 s waiting for a password/code form.
   That is a stalled request, not a refusal message from TikTok.
3. **17:09** — in the same space, Chrome to `https://www.tiktok.com/` →
   **`www.tiktok.com refused to connect` (ERR_CONNECTION_REFUSED)**.
4. **The control** — the throwaway's space (virginia) on the same phone: leak check green at 05:22
   (`208.214.162.185`, US, locked), and the robot posted to TikTok at 06:04 and read the profiles all
   day through it.

Earlier, same file, same phone: with the **HTTP** outbound the app answered "No internet connection";
with a **SOCKS5** outbound the request got through far enough that TikTok answered "Please try again or
log in with a different method". So the tunnel does reach TikTok's edge on a working exit — on this one
nothing gets past the TCP handshake.

Also measured 2026-11-22 02:00: **SOCKS5 UDP ASSOCIATE is refused by both gateways (`0x07`)** — a
proxy-vendor fact that is separate from this one.

## The question for the vendor

> On `us-ps-2-newyork` (65.195.107.138), TCP connections to `www.tiktok.com:443`, `www.instagram.com:443`
> and `1.1.1.1:443` are actively refused (RST) from a mobile client, while `us-ps-1-virginia`
> (208.214.162.185) on the same client, same app and same credentials works. Is the newyork exit
> egress-filtered, rate-limited, or is its gateway refusing CONNECT for those destinations? Same account,
> same plan.

Please also confirm whether the two exits are meant to be interchangeable — if newyork is deliberately
restricted, we need a second **virginia-class** exit, because two brands sharing one IP is exactly the
linkage the spaces exist to avoid.

## What is blocked until this is answered

- Speed's three logins and Timmy's three. Everything else is ready: both spaces are built, leak-configured,
  on New York time, apps installed, passwords in the vault, and the login flow itself (which now closes
  its job properly) stops cleanly at the spinner instead of lying about it.
- The `02:16` attempt to move Speed's space onto virginia failed at the import
  (`data/vpn-swap-u10.jsonl`: "the phone did not fetch the profile"). That is a robot-side bug to fix
  before any swap is attempted again.
