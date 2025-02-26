import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { DollarSign, Percent, Package, ArrowUp, ArrowDown } from 'lucide-react';
import { formatCurrency, formatPercent } from '../utils/formatters';

const B2BForm = ({ b2bData, setB2bData, b2bVolume, setB2bVolume, b2bResults }) => {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>B2B OEM Development</CardTitle>
            <CardDescription>Min. Order: {b2bData.minOrder} pairs</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex items-center">
                <DollarSign className="h-4 w-4 mr-2 text-blue-500" />
                <div>
                  <p className="text-sm text-gray-500">Cost Per Pair</p>
                  <p className="text-lg font-medium">{formatCurrency(b2bResults.costPerUnit)}</p>
                </div>
              </div>
              <div className="flex items-center">
                <DollarSign className="h-4 w-4 mr-2 text-green-500" />
                <div>
                  <p className="text-sm text-gray-500">Price Per Pair</p>
                  <p className="text-lg font-medium">{formatCurrency(b2bResults.pricePerUnit)}</p>
                </div>
              </div>
              <div className="flex items-center">
                <Package className="h-4 w-4 mr-2 text-purple-500" />
                <div>
                  <p className="text-sm text-gray-500">Total Order Value</p>
                  <p className="text-lg font-medium">{formatCurrency(b2bResults.totalOrderPrice)}</p>
                </div>
              </div>
              <div className="flex items-center">
                <Percent className="h-4 w-4 mr-2 text-orange-500" />
                <div>
                  <p className="text-sm text-gray-500">Profit Margin</p>
                  <p className="text-lg font-medium">{formatPercent(b2bResults.profitMargin)}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader>
            <CardTitle>Monthly B2B Projection</CardTitle>
            <CardDescription>Based on {b2bVolume} orders per month</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 gap-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <ArrowUp className="h-4 w-4 mr-2 text-green-500" />
                  <p>Monthly Revenue</p>
                </div>
                <p className="font-medium">{formatCurrency(b2bResults.monthlySales)}</p>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <ArrowDown className="h-4 w-4 mr-2 text-red-500" />
                  <p>Monthly Cost</p>
                </div>
                <p className="font-medium">{formatCurrency(b2bResults.monthlyCost)}</p>
              </div>
              <div className="flex items-center justify-between">
                <div className="flex items-center">
                  <DollarSign className="h-4 w-4 mr-2 text-blue-500" />
                  <p>Monthly Profit</p>
                </div>
                <p className="font-medium">{formatCurrency(b2bResults.monthlyProfit)}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* B2B Cost Inputs */}
      <Card>
        <CardHeader>
          <CardTitle>B2B Cost Parameters</CardTitle>
          <CardDescription>Adjust values to update calculations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm font-medium mb-1">Minimum Order (Pairs)</label>
              <input
                type="number"
                value={b2bData.minOrder}
                onChange={(e) => setB2bData({...b2bData, minOrder: parseFloat(e.target.value) || 0})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Materials Cost ($)</label>
              <input
                type="number"
                step="0.1"
                value={b2bData.materials}
                onChange={(e) => setB2bData({...b2bData, materials: parseFloat(e.target.value) || 0})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Labor Cost ($)</label>
              <input
                type="number"
                step="0.1"
                value={b2bData.labor}
                onChange={(e) => setB2bData({...b2bData, labor: parseFloat(e.target.value) || 0})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Overhead Cost ($)</label>
              <input
                type="number"
                step="0.1"
                value={b2bData.overhead}
                onChange={(e) => setB2bData({...b2bData, overhead: parseFloat(e.target.value) || 0})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Packaging Cost ($)</label>
              <input
                type="number"
                step="0.1"
                value={b2bData.packaging}
                onChange={(e) => setB2bData({...b2bData, packaging: parseFloat(e.target.value) || 0})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Shipping Cost ($)</label>
              <input
                type="number"
                step="0.1"
                value={b2bData.shipping}
                onChange={(e) => setB2bData({...b2bData, shipping: parseFloat(e.target.value) || 0})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Markup (%)</label>
              <input
                type="number"
                step="1"
                value={b2bData.markup}
                onChange={(e) => setB2bData({...b2bData, markup: parseFloat(e.target.value) || 0})}
                className="w-full p-2 border rounded"
              />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Monthly Orders</label>
              <input
                type="number"
                step="1"
                value={b2bVolume}
                onChange={(e) => setB2bVolume(parseInt(e.target.value) || 0)}
                className="w-full p-2 border rounded"
              />
            </div>
          </div>
        </CardContent>
      </Card>
    </>
  );
};

export default B2BForm;