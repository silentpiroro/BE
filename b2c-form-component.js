import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { formatCurrency, formatPercent } from '../utils/formatters';

const B2CForm = ({ b2cData, setB2cData, b2cResults }) => {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {b2cResults.packages.map((pkg, index) => (
          <Card key={index}>
            <CardHeader>
              <CardTitle>{pkg.name}</CardTitle>
              <CardDescription>{pkg.pairs} pairs per package</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Cost per Package:</span>
                  <span>{formatCurrency(pkg.totalCostPerPackage)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Price per Package:</span>
                  <span>{formatCurrency(pkg.pricePerPackage)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Profit per Package:</span>
                  <span>{formatCurrency(pkg.profit)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Profit Margin:</span>
                  <span>{formatPercent(pkg.profitMargin)}</span>
                </div>
                <div className="flex justify-between">
                  <span>Monthly Units Sold:</span>
                  <span>{pkg.volume}</span>
                </div>
                <div className="flex justify-between">
                  <span>Monthly Revenue:</span>
                  <span>{formatCurrency(pkg.monthlySales)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>B2C Monthly Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col items-center justify-center p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Monthly Revenue</p>
              <p className="text-2xl font-bold text-blue-600">{formatCurrency(b2cResults.totalMonthlySales)}</p>
            </div>
            <div className="flex flex-col items-center justify-center p-4 bg-red-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Monthly Cost</p>
              <p className="text-2xl font-bold text-red-600">{formatCurrency(b2cResults.totalMonthlyCost)}</p>
            </div>
            <div className="flex flex-col items-center justify-center p-4 bg-green-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Monthly Profit</p>
              <p className="text-2xl font-bold text-green-600">{formatCurrency(b2cResults.totalMonthlyProfit)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* B2C Product Parameters */}
      <Card>
        <CardHeader>
          <CardTitle>B2C Product Parameters</CardTitle>
          <CardDescription>Adjust product costs and sales projections</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {b2cData.packages.map((pkg, index) => (
              <div key={index} className="border p-4 rounded">
                <h3 className="font-medium mb-2">{pkg.name} ({pkg.pairs} pairs)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Cost Per Pair ($)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={pkg.costPerPair}
                      onChange={(e) => {
                        const newPackages = [...b2cData.packages];
                        newPackages[index].costPerPair = parseFloat(e.target.value) || 0;
                        setB2cData({...b2cData, packages: newPackages});
                      }}
                      className="w-full p-2 border rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Packaging Cost ($)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={pkg.packaging}
                      onChange={(e) => {
                        const newPackages = [...b2cData.packages];
                        newPackages[index].packaging = parseFloat(e.target.value) || 0;
                        setB2cData({...b2cData, packages: newPackages});
                      }}
                      className="w-full p-2 border rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Markup (%)</label>
                    <input
                      type="number"
                      step="1"
                      value={pkg.markup}
                      onChange={(e) => {
                        const newPackages = [...b2cData.packages];
                        newPackages[index].markup = parseFloat(e.target.value) || 0;
                        setB2cData({...b2cData, packages: newPackages});
                      }}
                      className="w-full p-2 border rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Monthly Sales Volume</label>
                    <input
                      type="number"
                      step="1"
                      value={b2cData.monthlyVolume.find(v => v.name === pkg.name)?.units || 0}
                      onChange={(e) => {
                        const newMonthlyVolume = [...b2cData.monthlyVolume];
                        const volumeIndex = newMonthlyVolume.findIndex(v => v.name === pkg.name);
                        if (volumeIndex >= 0) {
                          newMonthlyVolume[volumeIndex].units = parseInt(e.target.value) || 0;
                        }
                        setB2cData({...b2cData, monthlyVolume: newMonthlyVolume});
                      }}
                      className="w-full p-2 border rounded"
                    />
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </>
  );
};

export default B2CForm;