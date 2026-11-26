import 'fake-indexeddb/auto'
import { describe, expect, it } from 'vitest'
import { PendingCashSaleStore, type PendingCashSale } from './pendingCashSale'

const firstSale: PendingCashSale = {
  idempotency_key: 'sale-retry-key-1',
  sale_total_minor: 1250,
  request: {
    till_id: 4,
    till_session_id: 12,
    payment_method: 'CASH',
    expected_total: '12.50',
    amount_tendered: '20.00',
    items: [{
      product_id: 8,
      quantity: 1,
      unit_price: '12.50',
      tax_rate: '0',
      tax_inclusive: false,
    }],
    notes: 'Cash payment',
  },
}

function openDatabase(name: string): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(name, 1)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

describe('pending cash sale persistence', () => {
  it('restores the original request and idempotency key after reopening the database', async () => {
    const databaseName = `pending-sale-reload-${crypto.randomUUID()}`
    const first = new PendingCashSaleStore(databaseName)
    await first.save(3, firstSale)
    await first.close()

    const reopened = new PendingCashSaleStore(databaseName)
    expect(await reopened.load(3)).toEqual(firstSale)
    expect(await reopened.has(3)).toBe(true)
    expect(await reopened.has(5)).toBe(false)
    await reopened.close()
  })

  it('atomically prevents a changed checkout from replacing an unresolved sale', async () => {
    const databaseName = `pending-sale-claim-${crypto.randomUUID()}`
    const first = new PendingCashSaleStore(databaseName)
    const second = new PendingCashSaleStore(databaseName)
    const changedSale = {
      ...firstSale,
      idempotency_key: 'sale-retry-key-2',
      request: { ...firstSale.request, amount_tendered: '50.00' },
    }

    const results = await Promise.allSettled([
      first.save(3, firstSale),
      second.save(3, changedSale),
    ])
    expect(results.filter((result) => result.status === 'fulfilled')).toHaveLength(1)
    expect(results.filter((result) => result.status === 'rejected')).toHaveLength(1)
    expect([firstSale, changedSale]).toContainEqual(await first.load(3))
    await first.close()
    await second.close()
  })

  it('rejects persisted idempotency keys that exceed the API limit', async () => {
    const databaseName = `pending-sale-invalid-${crypto.randomUUID()}`
    const initializer = new PendingCashSaleStore(databaseName)
    await initializer.load(3)
    await initializer.close()

    const database = await openDatabase(databaseName)
    const transaction = database.transaction('pending_sales', 'readwrite')
    transaction.objectStore('pending_sales').put({
      userId: 3,
      sale: { ...firstSale, idempotency_key: 'x'.repeat(91) },
    })
    await new Promise<void>((resolve, reject) => {
      transaction.oncomplete = () => resolve()
      transaction.onabort = () => reject(transaction.error)
      transaction.onerror = () => reject(transaction.error)
    })
    database.close()

    const store = new PendingCashSaleStore(databaseName)
    await expect(store.load(3)).rejects.toThrow('pending sale record is invalid')
    await store.close()
  })
})
