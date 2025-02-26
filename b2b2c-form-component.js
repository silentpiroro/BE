import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/card';
import { formatCurrency, formatPercent } from '../utils/formatters';

const B2B2CForm = ({ b2b2cData, setB2b2cData, b2b2cResults }) => {
  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {b2b2cResults.packages.map((pkg, index) => (
          <Card key={index}>
            <CardHeader>
              <CardTitle>{pkg.name} Package</CardTitle>
              <CardDescription>{pkg.quantity} pairs with {b2b2cData.selectedDecorationMethod}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between">
                  <span>Cost per Package:</span>
                  <span>{formatCurrency(pkg.costPerPackage)}</span>
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
                  <span>Monthly Units:</span>
                  <span>{pkg.monthlySales}</span>
                </div>
                <div className="flex justify-between">
                  <span>Monthly Revenue:</span>
                  <span>{formatCurrency(pkg.monthlySalesValue)}</span>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
      
      <Card>
        <CardHeader>
          <CardTitle>B2B2C Monthly Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex flex-col items-center justify-center p-4 bg-blue-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Monthly Revenue</p>
              <p className="text-2xl font-bold text-blue-600">{formatCurrency(b2b2cResults.totalMonthlySales)}</p>
            </div>
            <div className="flex flex-col items-center justify-center p-4 bg-red-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Monthly Cost</p>
              <p className="text-2xl font-bold text-red-600">{formatCurrency(b2b2cResults.totalMonthlyCost)}</p>
            </div>
            <div className="flex flex-col items-center justify-center p-4 bg-green-50 rounded-lg">
              <p className="text-sm text-gray-500">Total Monthly Profit</p>
              <p className="text-2xl font-bold text-green-600">{formatCurrency(b2b2cResults.totalMonthlyProfit)}</p>
            </div>
          </div>
        </CardContent>
      </Card>
      
      {/* B2B2C Customization Options */}
      <Card>
        <CardHeader>
          <CardTitle>B2B2C Customization Parameters</CardTitle>
          <CardDescription>Select decoration method and adjust costs</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-2">Decoration Method:</label>
            <div className="flex space-x-4">
              <label className="flex items-center">
                <input
                  type="radio"
                  value="Printing"
                  checked={b2b2cData.selectedDecorationMethod === "Printing"}
                  onChange={() => setB2b2cData({...b2b2cData, selectedDecorationMethod: "Printing"})}
                  className="mr-2"
                />
                Printing
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="Embroidery"
                  checked={b2b2cData.selectedDecorationMethod === "Embroidery"}
                  onChange={() => setB2b2cData({...b2b2cData, selectedDecorationMethod: "Embroidery"})}
                  className="mr-2"
                />
                Embroidery
              </label>
              <label className="flex items-center">
                <input
                  type="radio"
                  value="Woven Label"
                  checked={b2b2cData.selectedDecorationMethod === "Woven Label"}
                  onChange={() => setB2b2cData({...b2b2cData, selectedDecorationMethod: "Woven Label"})}
                  className="mr-2"
                />
                Woven Label
              </label>
            </div>
          </div>
          
          <div className="space-y-6">
            {b2b2cData.packages.map((pkg, index) => (
              <div key={index} className="border p-4 rounded">
                <h3 className="font-medium mb-2">{pkg.name} Package ({pkg.quantity} pairs)</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">Base Sock Cost ($)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={pkg.baseSockCost}
                      onChange={(e) => {
                        const newPackages = [...b2b2cData.packages];
                        newPackages[index].baseSockCost = parseFloat(e.target.value) || 0;
                        setB2b2cData({...b2b2cData, packages: newPackages});
                      }}
                      className="w-full p-2 border rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Printing Cost ($)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={pkg.printingCost}
                      onChange={(e) => {
                        const newPackages = [...b2b2cData.packages];
                        newPackages[index].printingCost = parseFloat(e.target.value) || 0;
                        setB2b2cData({...b2b2cData, packages: newPackages});
                      }}
                      className="w-full p-2 border rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Embroidery Additional ($)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={pkg.embroideryAdditional}
                      onChange={(e) => {
                        const newPackages = [...b2b2cData.packages];
                        newPackages[index].embroideryAdditional = parseFloat(e.target.value) || 0;
                        setB2b2cData({...b2b2cData, packages: newPackages});
                      }}
                      className="w-full p-2 border rounded"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">Woven Label Additional ($)</label>
                    <input
                      type="number"
                      step="0.1"
                      value={pkg.wovenLabelAdditional}
                      onChange={(e) => {
                        const newPackages = [...b2b2cData.packages];
                        newPackages[index].wovenLabelAdditional = parseFloat(e.target.value) || 0;
                        setB2b2cData({...b2b2cData, packages: newPackages});
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
                        const newPackages = [...b2b2cData.packages];
                        newPackages[index].markup = parseFloat(e.target.value) || 0;
                        setB2b2cData({...b2b2cData, packages: newPackages});
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

export default B2B2CForm;