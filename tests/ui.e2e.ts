import { expect } from 'e2e';
import { test } from '@e2e-dev/web';

test('lists stock and rejects invalid stock', async ({ app, screen }) => {
  await app.open('/');
  await expect(screen.getByRole('heading', 'household-restock')).toBeVisible();
  await expect(screen.getByText('toilet-paper')).toBeVisible();

  const stock = screen.getByLabel('toilet-paper の在庫');
  await stock.fill('-1');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByRole('alert')).toContainText('0 以上の整数');
});

test('starts restock below threshold and approves without leaking secrets', async ({
  app,
  screen,
  browser,
}) => {
  await app.open('/');
  const stock = screen.getByLabel('toilet-paper の在庫');
  await stock.fill('1');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByText('AWAITING_APPROVAL')).toBeVisible();

  await screen.getByRole('button', '承認').tap();
  await expect(screen.getByText('APPROVED')).toBeVisible();
  await expect(screen.getByRole('button', '承認')).toBeDisabled();

  // 承認後の再送は拒否される（競合）
  // 無効ボタンは押せないので、却下も無効であることだけ見る
  await expect(screen.getByRole('button', '却下')).toBeDisabled();

  const html = await browser.evaluate(() => document.documentElement.outerHTML);
  const lowered = html.toLowerCase();
  expect(lowered.includes('tasktoken')).toBe(false);
  expect(lowered.includes('x-approval-secret')).toBe(false);
  expect(lowered.includes('secret-token-')).toBe(false);
});

test('reject path works from awaiting', async ({ app, screen }) => {
  await app.open('/');
  // 前テストの APPROVED が残っていても、占有解放後なら再起動できる
  await screen.getByLabel('toilet-paper の在庫').fill('9');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByRole('status')).toContainText('最新');

  await screen.getByLabel('toilet-paper の在庫').fill('0');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByText('AWAITING_APPROVAL')).toBeVisible();
  await screen
    .getByRole('row')
    .filter({ hasText: 'AWAITING_APPROVAL' })
    .getByRole('button', '却下')
    .tap();
  await expect(screen.getByText('REJECTED')).toBeVisible();
});
