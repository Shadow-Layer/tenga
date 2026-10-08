import React, { useState } from 'react'

type User = {
  id: number
  username: string
  email: string
  role: string
}

function apiFetch(path: string, opts: RequestInit = {}) {
  const token = localStorage.getItem('access_token')
  const headers: any = opts.headers || {}
  headers['Content-Type'] = 'application/json'
  if (token) headers['Authorization'] = `Bearer ${token}`
  return fetch(path, { ...opts, headers })
}

export default function AdminQuickStart({ user }: { user: User }) {
  const [msgs, setMsgs] = useState<string[]>([])
  const push = (m: string) => setMsgs((s) => [m, ...s].slice(0, 10))

  // State for forms
  const [locName, setLocName] = useState('Quick Location')
  const [locCode, setLocCode] = useState('QS_LOC')
  const [locDesc, setLocDesc] = useState('Location for quick testing')

  const [prodName, setProdName] = useState('Quick Coffee')
  const [prodSku, setProdSku] = useState('QS-COF-001')
  const [prodPrice, setProdPrice] = useState<number>(450)
  const [prodCost, setProdCost] = useState<number>(200)

  const [stockProductId, setStockProductId] = useState<number | ''>('')
  const [stockLocationId, setStockLocationId] = useState<number | ''>('')
  const [stockQty, setStockQty] = useState<number>(50)
  const [stockReason, setStockReason] = useState('PHYSICAL_COUNT_DISCREPANCY')

  const [tillLocationId, setTillLocationId] = useState<number | ''>('')
  const [tillCode, setTillCode] = useState('QS-TILL')
  const [tillName, setTillName] = useState('Quick Till')

  const [openTillId, setOpenTillId] = useState<number | ''>('')
  const [openingBalance, setOpeningBalance] = useState<number>(50000)

  const [saleTillId, setSaleTillId] = useState<number | ''>('')
  const [saleProductId, setSaleProductId] = useState<number | ''>('')
  const [saleQty, setSaleQty] = useState<number>(1)
  const [saleUnitPrice, setSaleUnitPrice] = useState<number>(450)

  const [verifyLocationId, setVerifyLocationId] = useState<number | ''>('')

  const [closeTillId, setCloseTillId] = useState<number | ''>('')
  const [closingAmount, setClosingAmount] = useState<number>(51000)

  async function createLocation() {
    try {
      const res = await apiFetch('/api/v1/locations', {
        method: 'POST',
        body: JSON.stringify({ name: locName, code: locCode, description: locDesc, organization_id: 1 }),
      })
      if (!res.ok) throw new Error(await res.text())
      const data = await res.json()
      push(`Location created: id=${data.id}`)
      setStockLocationId(data.id)
      setTillLocationId(data.id)
      setVerifyLocationId(data.id)
      setOpenTillId(data.id) // convenience
    } catch (err: any) {
      push(`Create location error: ${err.message}`)
    }
  }

  async function createProduct() {
    try {
      const res = await apiFetch('/api/v1/products', {
        method: 'POST',
        body: JSON.stringify({ name: prodName, sku: prodSku, category: 'General', price: prodPrice, cost: prodCost, organization_id: 1 }),
      })
      if (!res.ok) throw new Error(await res.text())
      const d = await res.json()
      push(`Product created: id=${d.id}`)
      setStockProductId(d.id)
      setSaleProductId(d.id)
    } catch (err: any) {
      push(`Create product error: ${err.message}`)
    }
  }

  async function addStock() {
    try {
      if (!stockProductId || !stockLocationId) return push('Set product_id and location_id first')
      const res = await apiFetch(`/api/v1/stock/stock/adjust?organization_id=1`, {
        method: 'POST',
        body: JSON.stringify({ product_id: Number(stockProductId), location_id: Number(stockLocationId), quantity: Number(stockQty), reason: stockReason, recorded_by_id: user.id }),
      })
      if (!res.ok) {
        const err = await res.json().catch(()=>null)
        throw new Error(err?.detail || JSON.stringify(err) || res.statusText)
      }
      const d = await res.json()
      push(`Stock adjusted: product=${d.product_id} qty=${d.quantity}`)
    } catch (err: any) {
      push(`Add stock error: ${err.message}`)
    }
  }

  async function createTill() {
    try {
      if (!tillLocationId) return push('Set location_id first')
      const res = await apiFetch('/api/v1/tills', {
        method: 'POST',
        body: JSON.stringify({ organization_id: 1, location_id: Number(tillLocationId), code: tillCode, name: tillName }),
      })
      if (!res.ok) throw new Error(await res.text())
      const d = await res.json()
      push(`Till created: id=${d.id}`)
      setOpenTillId(d.id)
      setSaleTillId(d.id)
      setCloseTillId(d.id)
    } catch (err: any) {
      push(`Create till error: ${err.message}`)
    }
  }

  async function openTill() {
    try {
      if (!openTillId) return push('Set till_id first')
      const res = await apiFetch(`/api/v1/tills/${openTillId}/open`, {
        method: 'POST',
        body: JSON.stringify({ user_id: user.id, opening_balance_cents: Number(openingBalance) }),
      })
      if (!res.ok) throw new Error(await res.text())
      const d = await res.json()
      push(`Till session opened: id=${d.id}`)
    } catch (err: any) {
      push(`Open till error: ${err.message}`)
    }
  }

  async function processSale() {
    try {
      if (!saleTillId || !saleProductId) return push('Set till_id and product_id first')
      const body = {
        till_id: Number(saleTillId),
        cashier_id: user.id,
        payment_method: 'cash',
        items: [{ product_id: Number(saleProductId), quantity: Number(saleQty), unit_price: Number(saleUnitPrice) }],
        is_offline: false,
      }
      const res = await apiFetch('/api/v1/sales', { method: 'POST', body: JSON.stringify(body) })
      if (!res.ok) {
        const errText = await res.text()
        throw new Error(errText)
      }
      const d = await res.json()
      push(`Sale created: id=${d.id} total=${d.total_amount_cents || 'n/a'}`)
    } catch (err: any) {
      push(`Process sale error: ${err.message}`)
    }
  }

  async function verifyStock() {
    try {
      if (!verifyLocationId) return push('Set location_id first')
      const res = await apiFetch(`/api/v1/stock/locations/${verifyLocationId}/stock`)
      if (!res.ok) throw new Error(await res.text())
      const d = await res.json()
      push(`Stock at location ${verifyLocationId}: ${JSON.stringify(d).slice(0,200)}`)
    } catch (err: any) {
      push(`Verify stock error: ${err.message}`)
    }
  }

  async function closeTill() {
    try {
      if (!closeTillId) return push('Set till_id first')
      const res = await apiFetch(`/api/v1/tills/${closeTillId}/close`, {
        method: 'POST',
        body: JSON.stringify({ user_id: user.id, closing_amount_cents: Number(closingAmount), notes: 'End of quick session' }),
      })
      if (!res.ok) throw new Error(await res.text())
      const d = await res.json()
      push(`Till closed: ${JSON.stringify(d).slice(0,120)}`)
    } catch (err: any) {
      push(`Close till error: ${err.message}`)
    }
  }

  return (
    <div>
      <h3 className="text-xl font-semibold mb-4">Admin Quick Actions</h3>

      <div className="grid md:grid-cols-2 gap-4">
        <div className="p-4 border rounded bg-white">
          <h4 className="font-semibold">1) Create Location</h4>
          <input className="w-full border px-2 py-1 my-1" value={locName} onChange={(e)=>setLocName(e.target.value)} />
          <input className="w-full border px-2 py-1 my-1" value={locCode} onChange={(e)=>setLocCode(e.target.value)} />
          <input className="w-full border px-2 py-1 my-1" value={locDesc} onChange={(e)=>setLocDesc(e.target.value)} />
          <button className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded" onClick={createLocation}>Create</button>
        </div>

        <div className="p-4 border rounded bg-white">
          <h4 className="font-semibold">2) Create Product</h4>
          <input className="w-full border px-2 py-1 my-1" value={prodName} onChange={(e)=>setProdName(e.target.value)} />
          <input className="w-full border px-2 py-1 my-1" value={prodSku} onChange={(e)=>setProdSku(e.target.value)} />
          <div className="flex gap-2">
            <input type="number" className="w-1/2 border px-2 py-1 my-1" value={prodPrice} onChange={(e)=>setProdPrice(Number(e.target.value))} />
            <input type="number" className="w-1/2 border px-2 py-1 my-1" value={prodCost} onChange={(e)=>setProdCost(Number(e.target.value))} />
          </div>
          <button className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded" onClick={createProduct}>Create</button>
        </div>

        <div className="p-4 border rounded bg-white">
          <h4 className="font-semibold">3) Add Stock</h4>
          <input placeholder="product_id" className="w-full border px-2 py-1 my-1" value={stockProductId} onChange={(e)=>setStockProductId(e.target.value ? Number(e.target.value) : '')} />
          <input placeholder="location_id" className="w-full border px-2 py-1 my-1" value={stockLocationId} onChange={(e)=>setStockLocationId(e.target.value ? Number(e.target.value) : '')} />
          <input type="number" className="w-full border px-2 py-1 my-1" value={stockQty} onChange={(e)=>setStockQty(Number(e.target.value))} />
          <select className="w-full border px-2 py-1 my-1" value={stockReason} onChange={(e)=>setStockReason(e.target.value)}>
            <option>PHYSICAL_COUNT_DISCREPANCY</option>
            <option>DAMAGE</option>
            <option>SHRINKAGE</option>
            <option>ADJUSTMENT</option>
          </select>
          <button className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded" onClick={addStock}>Adjust</button>
        </div>

        <div className="p-4 border rounded bg-white">
          <h4 className="font-semibold">4) Create Till</h4>
          <input placeholder="location_id" className="w-full border px-2 py-1 my-1" value={tillLocationId} onChange={(e)=>setTillLocationId(e.target.value ? Number(e.target.value) : '')} />
          <input className="w-full border px-2 py-1 my-1" value={tillCode} onChange={(e)=>setTillCode(e.target.value)} />
          <input className="w-full border px-2 py-1 my-1" value={tillName} onChange={(e)=>setTillName(e.target.value)} />
          <button className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded" onClick={createTill}>Create</button>
        </div>

        <div className="p-4 border rounded bg-white">
          <h4 className="font-semibold">5) Open Till Session</h4>
          <input placeholder="till_id" className="w-full border px-2 py-1 my-1" value={openTillId} onChange={(e)=>setOpenTillId(e.target.value ? Number(e.target.value) : '')} />
          <input type="number" className="w-full border px-2 py-1 my-1" value={openingBalance} onChange={(e)=>setOpeningBalance(Number(e.target.value))} />
          <button className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded" onClick={openTill}>Open</button>
        </div>

        <div className="p-4 border rounded bg-white">
          <h4 className="font-semibold">6) Process Sale</h4>
          <input placeholder="till_id" className="w-full border px-2 py-1 my-1" value={saleTillId} onChange={(e)=>setSaleTillId(e.target.value ? Number(e.target.value) : '')} />
          <input placeholder="product_id" className="w-full border px-2 py-1 my-1" value={saleProductId} onChange={(e)=>setSaleProductId(e.target.value ? Number(e.target.value) : '')} />
          <input type="number" className="w-full border px-2 py-1 my-1" value={saleQty} onChange={(e)=>setSaleQty(Number(e.target.value))} />
          <input type="number" className="w-full border px-2 py-1 my-1" value={saleUnitPrice} onChange={(e)=>setSaleUnitPrice(Number(e.target.value))} />
          <button className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded" onClick={processSale}>Sell</button>
        </div>

        <div className="p-4 border rounded bg-white">
          <h4 className="font-semibold">7) Verify Stock</h4>
          <input placeholder="location_id" className="w-full border px-2 py-1 my-1" value={verifyLocationId} onChange={(e)=>setVerifyLocationId(e.target.value ? Number(e.target.value) : '')} />
          <button className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded" onClick={verifyStock}>Check</button>
        </div>

        <div className="p-4 border rounded bg-white">
          <h4 className="font-semibold">8) Close Till Session</h4>
          <input placeholder="till_id" className="w-full border px-2 py-1 my-1" value={closeTillId} onChange={(e)=>setCloseTillId(e.target.value ? Number(e.target.value) : '')} />
          <input type="number" className="w-full border px-2 py-1 my-1" value={closingAmount} onChange={(e)=>setClosingAmount(Number(e.target.value))} />
          <button className="mt-2 bg-indigo-600 text-white px-3 py-1 rounded" onClick={closeTill}>Close</button>
        </div>
      </div>

      <div className="mt-6">
        <h4 className="font-semibold">Recent Actions</h4>
        <div className="bg-gray-50 p-3 rounded mt-2 text-sm">
          {msgs.length === 0 ? <div className="text-gray-500">No actions yet</div> : msgs.map((m, i) => <div key={i} className="py-1 border-b last:border-b-0">{m}</div>)}
        </div>
      </div>
    </div>
  )
}
