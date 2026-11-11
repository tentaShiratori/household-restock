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

test('approve reaches shipping wait without leaking secrets', async ({
  app,
  screen,
  browser,
}) => {
  await app.open('/');
  const stock = screen.getByLabel('toilet-paper の在庫');
  await stock.fill('1');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByTestId('status-AWAITING_APPROVAL')).toBeVisible();

  await screen.getByRole('button', '承認').tap();
  await expect(screen.getByTestId('status-SHIPPING_WAIT')).toBeVisible();
  await expect(screen.getByText('配送待ち')).toBeVisible();
  await expect(screen.getByRole('button', '承認')).toBeDisabled();
  await expect(screen.getByRole('button', '到着確認へ')).toBeEnabled();

  const html = await browser.evaluate(() => document.documentElement.outerHTML);
  const lowered = html.toLowerCase();
  expect(lowered.includes('tasktoken')).toBe(false);
  expect(lowered.includes('x-approval-secret')).toBe(false);
  expect(lowered.includes('secret-token-')).toBe(false);

  await screen
    .getByRole('row')
    .filter({ has: screen.getByTestId('status-SHIPPING_WAIT') })
    .getByRole('button', '到着確認へ')
    .tap();
  await expect(screen.getByTestId('status-ARRIVAL_CONFIRMED')).toBeVisible();
});

test('reject path and permanent failure labels', async ({ app, screen }) => {
  await app.open('/');
  await screen.getByLabel('toilet-paper の在庫').fill('9');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByRole('status')).toContainText('最新');

  await screen.getByLabel('toilet-paper の在庫').fill('0');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByTestId('status-AWAITING_APPROVAL')).toBeVisible();
  await screen
    .getByRole('row')
    .filter({ has: screen.getByTestId('status-AWAITING_APPROVAL') })
    .getByRole('button', '却下')
    .tap();
  await expect(screen.getByTestId('status-REJECTED')).toBeVisible();

  await screen.getByLabel('toilet-paper の注文失敗モード').selectOption('permanent');
  await screen.getByLabel('toilet-paper の在庫').fill('9');
  await screen.getByRole('button', '更新').tap();
  await screen.getByLabel('toilet-paper の在庫').fill('0');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByTestId('status-AWAITING_APPROVAL')).toBeVisible();
  await screen
    .getByRole('row')
    .filter({ has: screen.getByTestId('status-AWAITING_APPROVAL') })
    .getByRole('button', '承認')
    .tap();
  await expect(screen.getByTestId('status-ORDER_FAILED')).toBeVisible();
  await expect(screen.getByText('失敗')).toBeVisible();
});

test('advance delivery from shipping wait', async ({ app, screen }) => {
  await app.open('/');
  await screen.getByLabel('toilet-paper の注文失敗モード').selectOption('succeed');
  await screen.getByLabel('toilet-paper の在庫').fill('9');
  await screen.getByRole('button', '更新').tap();
  await screen.getByLabel('toilet-paper の在庫').fill('0');
  await screen.getByRole('button', '更新').tap();
  await expect(screen.getByTestId('status-AWAITING_APPROVAL')).toBeVisible();
  await screen
    .getByRole('row')
    .filter({ has: screen.getByTestId('status-AWAITING_APPROVAL') })
    .getByRole('button', '承認')
    .tap();
  await expect(screen.getByTestId('status-SHIPPING_WAIT')).toBeVisible();
  await screen
    .getByRole('row')
    .filter({ has: screen.getByTestId('status-SHIPPING_WAIT') })
    .getByRole('button', '到着確認へ')
    .tap();
  await expect(screen.getByTestId('status-ARRIVAL_CONFIRMED')).toBeVisible();
  await expect(screen.getByText('到着確認')).toBeVisible();
});
