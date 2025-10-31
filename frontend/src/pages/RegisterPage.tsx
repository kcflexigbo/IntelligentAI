import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import api from '../services/api';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

// A simple placeholder for the logo, you can replace this with an SVG or an <img> tag
const Logo = () => (
  <div className="flex items-center gap-2">
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M12 2L2 7V17L12 22L22 17V7L12 2Z" fill="oklch(var(--primary))" />
      <path d="M2 7L12 12L22 7" stroke="oklch(var(--primary-foreground))" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M12 22V12" stroke="oklch(var(--primary-foreground))" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
    <span className="text-xl font-bold text-foreground">IntelligentAI</span>
  </div>
);

// A placeholder for the 3D graphic. Replace this with your own illustration.
const AuthGraphic = () => (
  <div className="w-full h-full bg-gradient-to-br from-primary to-indigo-700 overflow-hidden">
    <img
      className="w-full h-full object-cover"
      src="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcRQenjW49W8L8xA0S2R5jU6vvoDrtPYxMC_3HtUM4sPewDhc4vIFEGcPLoNafP-3IpM2pE&usqp=CAU"
      alt="Auth Graphic"
    />
  </div>
);

const RegisterPage = () => {
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [error, setError] = useState<string>('');
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError('');
    try {
      await api.post('/auth/register', { email, password });
      navigate('/login');
    } catch (err) {
      setError('Failed to register. The email might already be in use.');
    }
  };

  return (
    <div className="flex min-h-screen w-full bg-background">
      {/* Left Column - Graphic */}
      <div className="hidden lg:flex lg:w-1/2 items-center justify-center">
        <AuthGraphic />
      </div>

      {/* Right Column - Form */}
      <div className="flex w-full lg:w-1/2 items-center justify-center p-8">
        <div className="w-full max-w-md space-y-8">
          <div className="flex justify-start">
            <Logo />
          </div>

          <div>
            <h1 className="text-3xl font-bold text-foreground">
              Create an Account
            </h1>
            <p className="mt-2 text-muted-foreground">
              Get started by creating a new account.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@example.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="h-12 px-4 bg-secondary border-border focus:bg-background"
              />
            </div>

            <div className="grid gap-2">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                placeholder="Create a strong password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="h-12 px-4 bg-secondary border-border focus:bg-background"
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button type="submit" className="w-full h-12 text-base font-semibold">
              Sign Up
            </Button>
          </form>

          <p className="text-center text-sm text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="font-semibold text-primary hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
};

export default RegisterPage;