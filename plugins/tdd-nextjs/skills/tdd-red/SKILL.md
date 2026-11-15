---
name: tdd-red
description: TDD の Red フェーズ。失敗する Vitest テスト（`it` 1つ）を1つだけ追加し、期待どおりに失敗することを確認する。Next.js（App Router）の lib / hook / Client Component / Server Action / Route Handler をテスト種別ごとの作法で書く。通常は /tdd から呼ばれる。単独では「失敗するテストを1つ書いて」と頼まれたときに使う。
argument-hint: <workflow_id> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(yarn:*)
  - Bash(npx:*)
  - Bash(npm:*)
  - Bash(pnpm:*)
  - Grep
  - Glob
  - TaskGet
  - Bash(date:*)
examples:
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。今サイクルのテストを1つだけ（1つの `it`）追加し、期待通り失敗することを確認する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（置き場の方針・パス・不変条件・テストコマンド）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `state-machine.md`

> 🔴 一度に1テストケースのみ。複数追加は不変条件違反。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が存在しないことを Read で確認（存在＝前サイクル未完了 → `/tdd-commit {id}` 案内し中断）。`completed_cycles` 長 == `current_cycle - 1` を確認。

## 1. コンテキスト
`workflow-{id}.json` を Read（`target_files`, `patterns`(test_kind/environment/uses_api/uses_query/uses_auth/uses_next_runtime), `current_cycle`, `user_instructions`）。`todo_task_id` で TaskGet し `cycle_plan` の該当エントリ（`title`, `kind`）を特定。
`vitest.setup.ts` と `test/render.tsx`（テストヘルパ）を Read し、何がグローバルに配線済みか（jest-dom・cleanup・MSW server・`next/font` スタブ）を把握する。配線済みのものをテストファイルで重ねて書かない。

## 2. テストファイル決定
`$1` 指定があればそれ。無ければ実装と同ディレクトリの `*.test.ts(x)`（既存ファイルへの追記を優先、無ければ新規）。
- `lib/price.ts` → `lib/price.test.ts`、`features/reservations/hooks/useReservations.ts` → `useReservations.test.tsx`、`ReservationForm.tsx` → `ReservationForm.test.tsx`、`app/(app)/reservations/actions.ts` → `actions.test.ts`。
- JSX を書くテストは `.test.tsx`、書かないテストは `.test.ts`。
- 既存の配置に揺れがあれば Glob で数え多数派に合わせる（`__tests__/` の慣習があればそちらに従う）。
- `page.tsx` / `layout.tsx`（Server Component）をテスト対象にしない。そこにしか置き場が無いロジックなら、切り出し先（`lib/` の関数 or Client Component / hook）のテストとして書く。切り出し先が計画と違う場合は停止条件#1 として報告。

## 2-b. 既存テストへの影響確認
公開インターフェイスの変更は既存テストを壊す。変更する場合は参照箇所を Grep し、必要なら本サイクルで合わせて更新（振る舞いの意味は変えない）：
- 関数のシグネチャ・エクスポート名
- component の props（必須化・型変更）、hook の返り値の形
- query key（`invalidateQueries` や `setQueryData` で同じ key を参照している箇所）
- MSW の共通 handler（正常系のレスポンスを変えると、それに依存する既存テストが壊れる）
- OpenAPI の型（`pnpm gen:api` で再生成すると型が変わる。API 契約そのものの変更は停止条件#2）

## 3. テスト追加（テスト種別ごとの必須パターン）
既存の近いテストを Read し慣習に揃える。booking-web の必須パターンを守る：

### lib（純粋関数。node 環境）
```ts
// @vitest-environment node
import { describe, expect, it } from 'vitest'
import { calcTotalPrice } from './price'

describe('calcTotalPrice', () => {
  it('2泊なら1泊料金の2倍を返す', () => {
    expect(calcTotalPrice({ nightly: 8000, nights: 2 })).toBe(16000)
  })
})
```
- 時刻・乱数は引数で受け取る（`new Date()` / `Math.random()` を関数内で直接呼ばない）。どうしても必要なら `vi.useFakeTimers()` + `vi.setSystemTime()` を使い、`afterEach` で `vi.useRealTimers()`。
- 正常系・境界（0・上限・端数）・不正入力は別サイクルに分ける。

### component（Client Component。RTL）
```tsx
import { describe, expect, it } from 'vitest'
import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { renderWithProviders } from '@/test/render'
import { ReservationForm } from './ReservationForm'

describe('ReservationForm', () => {
  it('日付が重複しているとエラーを表示し、送信ボタンを無効にする', async () => {
    const user = userEvent.setup()
    renderWithProviders(<ReservationForm existing={[createReservation({ date: '2026-12-24' })]} />)

    await user.type(screen.getByLabelText('宿泊日'), '2026-12-24')

    expect(await screen.findByRole('alert')).toHaveTextContent('この日は予約済みです')
    expect(screen.getByRole('button', { name: '予約する' })).toBeDisabled()
  })
})
```
- 要素は role / アクセシブルネーム（`getByRole` / `getByLabelText`）。`data-testid` は最後の手段。Tailwind のクラス名は検証しない。
- 非同期の表示（API 応答後・遷移後）は `findBy*` で待つ。`waitFor` の中で副作用（クリック等）を起こさない。手で `act()` を書かない（RTL と user-event が包む）。
- `userEvent.setup()` は各 `it` の中で作る。fake timers と併用するときは `userEvent.setup({ advanceTimers: vi.advanceTimersByTime })`。
- 初期表示・ユーザー操作・ローディング・エラー・空状態は別サイクルに分ける。

### hook（TanStack Query を含む）
```tsx
import { renderHook, waitFor } from '@testing-library/react'
import { createWrapper } from '@/test/render'   // 各呼び出しで新しい QueryClient（retry: false）を作る wrapper

it('予約一覧を取得して返す', async () => {
  const { result } = renderHook(() => useReservations(), { wrapper: createWrapper() })
  await waitFor(() => expect(result.current.isSuccess).toBe(true))
  expect(result.current.data).toHaveLength(2)
})
```
- `QueryClient` を `describe` の外やモジュールスコープで1つだけ作らない（キャッシュがテスト間に漏れる。不変条件#3）。
- mutation は「成功後に関連 query が無効化されて再取得される」を、MSW の呼び出し回数やその後の表示で検証する（`invalidateQueries` を spy して呼ばれたことだけを見るのは実装詳細寄り）。

### API 連携（MSW）
```ts
import { http, HttpResponse } from 'msw'
import { server } from '@/test/msw/server'

server.use(
  http.get('*/reservations', () => HttpResponse.json({ message: 'error' }, { status: 500 })),
)
```
- 正常系は共通 handler（`test/msw/handlers.ts`）、異常系（4xx/5xx・ネットワークエラー `HttpResponse.error()`）は各テストで `server.use(...)` 上書き。実通信はしない。
- レスポンスは OpenAPI の型（`components['schemas']['Reservation']`）に合わせ、ファクトリで作る。生成された型ファイルは手で編集しない。

### 認証（Auth0 SPA）
```ts
vi.mock('@auth0/auth0-react', () => ({
  useAuth0: () => ({ isAuthenticated: true, isLoading: false, user: { sub: 'auth0|1' }, getAccessTokenSilently: vi.fn().mockResolvedValue('test-token') }),
}))
```
- 未認証・読み込み中の出し分けは別サイクル。`renderWithProviders` に認証状態を渡せる形があればそちらを使う。
- API クライアントのトークン取得は注入で差し替える（クライアント内部で `useAuth0` を直接呼ばない）。

### Next.js のランタイム API
```ts
const { push } = vi.hoisted(() => ({ push: vi.fn() }))   // vi.mock は巻き上げられるので、ファクトリから参照する変数は vi.hoisted で作る
vi.mock('next/navigation', () => ({
  useRouter: () => ({ push, replace: vi.fn(), refresh: vi.fn(), back: vi.fn() }),
  usePathname: () => '/reservations',
  useSearchParams: () => new URLSearchParams('date=2026-12-24'),
}))
```
- 遷移は「`push` が期待した URL で呼ばれた」を検証する（実際の遷移は E2E の範囲）。

### server-action（node 環境）
```ts
// @vitest-environment node
import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import { createReservation } from './actions'

vi.mock('next/cache', () => ({ revalidatePath: vi.fn() }))
vi.mock('next/navigation', () => ({ redirect: vi.fn() }))

it('予約を作成したら一覧を再検証して詳細へリダイレクトする', async () => {
  const formData = new FormData()
  formData.set('date', '2026-12-24')
  await createReservation(formData)
  expect(revalidatePath).toHaveBeenCalledWith('/reservations')
  expect(redirect).toHaveBeenCalledWith('/reservations/1')
})
```
- `redirect()` は本物だと例外を投げて処理を止める。モックしない場合は `rejects.toThrow('NEXT_REDIRECT')` で検証する（どちらかに揃える）。
- `server-only` を import しているモジュールは jsdom で落ちる。node 環境で実行するか、`vitest.setup.ts` で `vi.mock('server-only', () => ({}))`。

### route-handler（node 環境）
```ts
// @vitest-environment node
it('date が無ければ 400 を返す', async () => {
  const res = await GET(new Request('http://localhost/api/availability'))
  expect(res.status).toBe(400)
})
```

## 4. 失敗確認
```bash
pnpm vitest run {test_file_path} -t "{テストケース名}"
```
期待される失敗: 未定義（module/export/component）、`Unable to find role/label`、値の不一致、`expected "spy" to be called`、MSW handler が返すデータが表示されない。
予期しない失敗はテスト側を修正して再実行する。実装を書き始めてはいけない。典型:
- `document is not defined` → environment が node になっている（jsdom が要るテスト）。
- `Invalid hook call` / `No QueryClient set` → wrapper（`renderWithProviders` / `createWrapper`）を通していない。
- `[MSW] Error: intercepted a request without a matching request handler` → handler の URL の書き方（`*/path`・ベース URL）の誤り。
- `invariant expected app router to be mounted` → `next/navigation` のモック漏れ。
- `toBeInTheDocument is not a function` → `vitest.setup.ts` で jest-dom を読み込んでいない。
- 前のテストの DOM が残っている → `cleanup` が配線されていない（`globals: false` の場合）。

## 5. 状態更新
`current-cycle.json` を workflow-schema 準拠で Write（`phase:"red"`, `test_file_path`, `test_name`（`-t` に渡すケース名）, `test_case_count`（`test_file_path` 内の `it(` / `test(` / `it.each` / `test.each` の定義数。Evac(review) の基準値）, `test_details`(error_type/message), `created_at`/`updated_at`）。

## 6. サマリ（簡潔）
テストファイル / 追加した1ケース / 期待通りの失敗 / 適用パターン（role 取得・user-event・MSW・QueryClient wrapper・Next.js モック 等）/ 次は Green。承認ゲート①は state-machine に従う（tdd 側が判断）。

## エラー
- テストファイル決定不能: `$1` 明示 or タスクに対象名（component / hook / 関数名）追記を案内。
- テスト基盤が未整備（RTL・jsdom・`vitest.setup.ts` が無い）: 設計判断（依存追加）なので停止し、`/tdd-bootstrap --force` でのセットアップ提案を案内する。
- ファクトリ・`renderWithProviders` 未定義: 最初に必要になったサイクルで、テストと一緒に最小限を追加する（ヘルパの充実は Refactor で）。
- 型エラーでテストが書けない: 実装側の型・export が未定義なのが原因ならそれが期待される失敗（そのまま Green へ）。設計上の型の矛盾なら停止条件#8 として報告。
