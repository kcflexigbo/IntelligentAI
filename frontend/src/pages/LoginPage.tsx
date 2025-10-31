import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardFooter } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Brain } from 'lucide-react';

const LoginPage = () => {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
    } catch (err) {
      setError('Failed to log in. Please check your credentials.');
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gradient-to-br from-blue-50 to-blue-100">
      <Card className="w-full max-w-lg shadow-lg border-0 bg-white">
        <div className="flex flex-col items-center pt-8 pb-2">
          <div className="w-16 h-16 rounded-2xl bg-blue-600 flex items-center justify-center mb-4">
            <Brain className="w-10 h-10 text-white" strokeWidth={2} />
          </div>
          <h1 className="text-2xl font-bold text-blue-600 mb-2 text-center">
            Intelligent Learning Assistant
          </h1>
          <p className="text-gray-500 text-sm text-center">
            Sign in to continue learning
          </p>
        </div>
        <form onSubmit={handleSubmit}>
          <CardContent className="grid gap-5 pt-6 px-8">
            <div className="grid gap-2">
              <Label htmlFor="email" className="text-sm font-medium text-gray-700">
                Email
              </Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 px-4 bg-blue-50 border-blue-200 focus:bg-white focus:border-blue-400"
              />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="password" className="text-sm font-medium text-gray-700">
                Password
              </Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-12 px-4 bg-blue-50 border-blue-200 focus:bg-white focus:border-blue-400"
              />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
            <Button 
              type="submit" 
              className="w-full h-12 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg shadow-sm transition-all mt-2"
            >
              Sign In
            </Button>
          </CardContent>
        </form>
        <CardFooter className="flex justify-center text-sm pb-8 pt-4">
          <p className="text-gray-600 text-center">
            Don't have an account?{" "}
            <Link to="/register" className="text-blue-600 hover:text-blue-700 font-medium hover:underline">
              Sign up
            </Link>
          </p>
        </CardFooter>
      </Card>
    </div>
  );
};

export default LoginPage;